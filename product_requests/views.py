from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import ProductRequest, RequestItem, SupplierResponse
from .serializers import ProductRequestSerializer, SupplierResponseSerializer
from users.permissions import IsSupplier, IsClient, IsSupplierStaff
from django.contrib.auth import get_user_model
from django.db.models import Q
from notifications.services import (
    notify_supplier_new_request,
    notify_client_response,
    notify_client_status_update
)
from catalog.models import Product
from users.models import BusinessClient

User = get_user_model()


def supplier_business(user):
    return user if user.role == User.Role.SUPPLIER else user.business_supplier

class ProductRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ProductRequestSerializer

    def get_queryset(self):
        user = self.request.user
        business = supplier_business(user)
        if business:
            return ProductRequest.objects.filter(
                supplier=business
            ).prefetch_related('items__product').select_related('client', 'supplier', 'response')
        return ProductRequest.objects.filter(
            client=user
        ).prefetch_related('items__product').select_related('client', 'supplier', 'response')

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        if self.action in ['respond', 'update_status']:
            return [permissions.IsAuthenticated(), IsSupplierStaff()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        is_sales_rep = request.user.role == User.Role.SALES_REP
        is_business_staff = request.user.role in [User.Role.SUPPLIER, User.Role.SALES_REP]
        if request.user.role != User.Role.CLIENT and not is_business_staff:
            return Response({'detail': 'Only clients or sales representatives can create requests.'}, status=status.HTTP_403_FORBIDDEN)
        if not request.user.is_phone_verified:
            return Response(
                {'detail': 'Verify your phone number before sending requests'},
                status=status.HTTP_403_FORBIDDEN
            )
        items_data = request.data.get('items', [])
        if not items_data:
            return Response(
                {'detail': 'Заявка должна содержать хотя бы один товар.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # validate all products belong to the same supplier
        supplier_ids = set()
        products = []
        for item in items_data:
            try:
                product = Product.objects.get(id=item['product_id'])
                products.append((product, item['quantity']))
                supplier_ids.add(product.supplier.id)
            except Product.DoesNotExist:
                return Response(
                    {'detail': f'Товар {item["product_id"]} не найден.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if len(supplier_ids) > 1:
            return Response(
                {'detail': 'Все товары в заявке должны быть от одного поставщика.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        supplier = products[0][0].supplier
        if is_sales_rep and supplier != request.user.business_supplier:
            return Response({'detail': 'You can only create requests for your supplier business.'}, status=status.HTTP_403_FORBIDDEN)

        if is_business_staff:
            business_client_id = request.data.get('business_client_id')
            try:
                business_client = BusinessClient.objects.get(id=business_client_id, supplier=supplier)
            except (User.DoesNotExist, ValueError, TypeError):
                return Response({'detail': 'Choose a valid client.'}, status=status.HTTP_400_BAD_REQUEST)
            except BusinessClient.DoesNotExist:
                return Response({'detail': 'Choose a valid client.'}, status=status.HTTP_400_BAD_REQUEST)
            if is_sales_rep and business_client.sales_rep_id != request.user.id:
                return Response({'detail': 'This client is assigned to another representative.'}, status=status.HTTP_403_FORBIDDEN)
        else:
            client_user = request.user
            business_client = None

        # check stock for all items
        for product, quantity in products:
            if quantity > product.stock_quantity:
                return Response(
                    {'detail': f'Недостаточно товара "{product.name}". Доступно: {product.stock_quantity}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # calculate total
        total_price = sum(product.price * quantity for product, quantity in products)

        # create request
        product_request = ProductRequest.objects.create(
            client=client_user,
            business_client=business_client,
            supplier=supplier,
            sales_rep=request.user if is_sales_rep else None,
            note=request.data.get('note', ''),
            delivery_address=request.data.get('delivery_address', business_client.address if business_client else ''),
            delivery_latitude=request.data.get('delivery_latitude') or (business_client.latitude if business_client else None),
            delivery_longitude=request.data.get('delivery_longitude') or (business_client.longitude if business_client else None),
            desired_delivery_date=request.data.get('desired_delivery_date') or None,
            contact_phone=request.data.get('contact_phone', business_client.phone if business_client else ''),
            total_price=total_price,
        )

        # create items
        for product, quantity in products:
            RequestItem.objects.create(
                request=product_request,
                product=product,
                quantity=quantity,
                price_at_request=product.price,
                total=product.price * quantity,
            )

        notify_supplier_new_request(product_request)
        serializer = self.get_serializer(product_request)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        product_request = self.get_object()
        if request.user.role == 'client':
            if product_request.status not in ['pending']:
                return Response(
                    {'detail': 'Заявку нельзя редактировать после принятия поставщиком.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return super().partial_update(request, *args, **kwargs)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsSupplier])
    def respond(self, request, pk=None):
        product_request = self.get_object()

        if product_request.supplier != supplier_business(request.user):
            return Response(
                {'detail': 'Вы можете отвечать только на свои заявки.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if hasattr(product_request, 'response'):
            return Response(
                {'detail': 'Вы уже ответили на эту заявку.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = SupplierResponseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(supplier=request.user, request=product_request)
            product_request.status = ProductRequest.Status.ACCEPTED
            product_request.save()
            notify_client_response(product_request)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAuthenticated, IsSupplier])
    def update_status(self, request, pk=None):
        product_request = self.get_object()
        new_status = request.data.get('status')

        allowed = [ProductRequest.Status.FULFILLED, ProductRequest.Status.DECLINED]
        if new_status not in [s.value for s in allowed]:
            return Response(
                {'detail': 'Статус должен быть fulfilled или declined.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_status == ProductRequest.Status.FULFILLED:
            for item in product_request.items.all():
                product = item.product
                if product.stock_quantity < item.quantity:
                    return Response(
                        {'detail': f'Недостаточно товара "{product.name}" на складе.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                product.stock_quantity -= item.quantity
                product.save()

        product_request.status = new_status
        product_request.save()
        notify_client_status_update(product_request)
        return Response({'status': new_status})
