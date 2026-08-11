import calendar
from decimal import Decimal

from django.utils import timezone
from django.db.models import Sum, F
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from users.models import User
from product_requests.models import ProductRequest, RequestItem
from .models import Expense, WorkerBonus
from .serializers import ExpenseSerializer, WorkerBonusSerializer


class IsSupplier(permissions.BasePermission):
    """The whole finance tab is supplier-only — not even sales reps get
    access, since it exposes salary figures for every worker."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.SUPPLIER


def _period_bounds(period):
    """Calendar-based bounds, not a rolling N-day window — 'day' means
    today, 'month' means the current calendar month, matching how a
    supplier actually thinks about "today's" or "this month's" numbers."""
    today = timezone.localdate()
    if period == 'day':
        return today, today, 1
    # month
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    start = today.replace(day=1)
    return start, today, days_in_month


class ExpenseListCreateView(APIView):
    permission_classes = [IsSupplier]

    def get(self, request):
        period = request.query_params.get('period', 'month')
        start, end, _ = _period_bounds(period)
        expenses = Expense.objects.filter(supplier=request.user, date__gte=start, date__lte=end)
        return Response(ExpenseSerializer(expenses, many=True).data)

    def post(self, request):
        serializer = ExpenseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        expense = serializer.save(supplier=request.user, created_by=request.user)
        return Response(ExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)


class ExpenseDetailView(APIView):
    permission_classes = [IsSupplier]

    def delete(self, request, pk):
        try:
            expense = Expense.objects.get(id=pk, supplier=request.user)
        except Expense.DoesNotExist:
            return Response({'detail': 'Расход не найден.'}, status=status.HTTP_404_NOT_FOUND)
        expense.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkerBonusListCreateView(APIView):
    permission_classes = [IsSupplier]

    def get(self, request):
        period = request.query_params.get('period', 'month')
        start, end, _ = _period_bounds(period)
        bonuses = WorkerBonus.objects.filter(supplier=request.user, date__gte=start, date__lte=end)
        return Response(WorkerBonusSerializer(bonuses, many=True).data)

    def post(self, request):
        worker_id = request.data.get('worker')
        try:
            worker = User.objects.get(id=worker_id, role=User.Role.SALES_REP, business_supplier=request.user)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({'detail': 'Выберите корректного сотрудника из вашей компании.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = WorkerBonusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bonus = serializer.save(supplier=request.user, worker=worker, created_by=request.user)
        return Response(WorkerBonusSerializer(bonus).data, status=status.HTTP_201_CREATED)


class WorkerBonusDetailView(APIView):
    permission_classes = [IsSupplier]

    def delete(self, request, pk):
        try:
            bonus = WorkerBonus.objects.get(id=pk, supplier=request.user)
        except WorkerBonus.DoesNotExist:
            return Response({'detail': 'Бонус не найден.'}, status=status.HTTP_404_NOT_FOUND)
        bonus.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FinanceSummaryView(APIView):
    permission_classes = [IsSupplier]

    def get(self, request):
        period = request.query_params.get('period', 'month')
        include_bonuses = request.query_params.get('include_bonuses', 'true').lower() != 'false'
        start, end, days_in_month = _period_bounds(period)
        supplier = request.user

        fulfilled = ProductRequest.objects.filter(
            supplier=supplier, status='fulfilled',
            updated_at__date__gte=start, updated_at__date__lte=end,
        )
        revenue = fulfilled.aggregate(total=Sum('total_price'))['total'] or Decimal('0')

        cogs = RequestItem.objects.filter(request__in=fulfilled).aggregate(
            total=Sum(F('quantity') * F('product__cost_price'))
        )['total'] or Decimal('0')

        # Salary is a monthly figure — for a single day's view, prorate it
        # across the days in the current month rather than showing the
        # full month's salary as "today's" expense.
        workers = User.objects.filter(business_supplier=supplier, role=User.Role.SALES_REP)
        monthly_salary_total = workers.aggregate(total=Sum('base_salary'))['total'] or Decimal('0')
        salary_expense = monthly_salary_total if period == 'month' else (monthly_salary_total / days_in_month)

        bonuses_qs = WorkerBonus.objects.filter(supplier=supplier, date__gte=start, date__lte=end)
        bonuses_total = bonuses_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        if not include_bonuses:
            bonuses_total = Decimal('0')

        expenses_qs = Expense.objects.filter(supplier=supplier, date__gte=start, date__lte=end)
        manual_expenses_total = expenses_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        expenses_by_category = {
            item['category']: float(item['total'])
            for item in expenses_qs.values('category').annotate(total=Sum('amount'))
        }

        total_expenses = cogs + salary_expense + bonuses_total + manual_expenses_total
        net_profit = revenue - total_expenses
        margin_percent = float((net_profit / revenue) * 100) if revenue > 0 else 0

        return Response({
            'period': period,
            'start_date': str(start),
            'end_date': str(end),
            'revenue': float(revenue),
            'cost_of_goods': float(cogs),
            'salary_expense': float(round(salary_expense, 2)),
            'salary_expense_monthly_total': float(monthly_salary_total),
            'bonuses_total': float(bonuses_total),
            'bonuses_included': include_bonuses,
            'manual_expenses_total': float(manual_expenses_total),
            'expenses_by_category': expenses_by_category,
            'total_expenses': float(total_expenses),
            'net_profit': float(net_profit),
            'margin_percent': round(margin_percent, 1),
            'fulfilled_orders': fulfilled.count(),
            'worker_count': workers.count(),
        })