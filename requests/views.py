from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import ProductRequest, SupplierResponse
from .serializers import ProductRequestSerializer, SupplierResponseSerializer
from users.permissions import IsSupplier, IsClient
from notifications.services import (
    notify_supplier_new_request,
    notify_client_response,
    notify_client_status_update
)
class ProductRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ProductRequestSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'supplier':
            # supplier sees requests for their products
            return ProductRequest.objects.filter(
                product__supplier=user
            ).select_related('client', 'product', 'response')
        # client sees only their own requests
        return ProductRequest.objects.filter(
            client=user
        ).select_related('client', 'product', 'response')

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsClient()]
        if self.action in ['respond', 'update_status']:
            return [permissions.IsAuthenticated(), IsSupplier()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']

        # check stock availability
        if quantity > product.stock_quantity:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                f'Недостаточно товара. Доступно: {product.stock_quantity}'
            )

        total_price = product.price * quantity
        product_request = serializer.save(
            client=self.request.user,
            total_price=total_price
        )
        notify_supplier_new_request(product_request)
        
    # POST /api/requests/{id}/respond/
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsSupplier])
    def respond(self, request, pk=None):
        product_request = self.get_object()

        # make sure this supplier owns the product
        if product_request.product.supplier != request.user:
            return Response(
                {'detail': 'You can only respond to requests for your own products.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # check if response already exists
        if hasattr(product_request, 'response'):
            return Response(
                {'detail': 'You have already responded to this request.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = SupplierResponseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                supplier=request.user,
                request=product_request
            )
            # update request status to accepted
            product_request.status = ProductRequest.Status.ACCEPTED
            product_request.save()
            notify_client_response(product_request)  # ← add this

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

        # decrease stock when fulfilled
        if new_status == ProductRequest.Status.FULFILLED:
            product = product_request.product
            if product.stock_quantity < product_request.quantity:
                return Response(
                    {'detail': 'Недостаточно товара на складе.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            product.stock_quantity -= product_request.quantity
            product.save()

        product_request.status = new_status
        product_request.save()
        notify_client_status_update(product_request)
        return Response({'status': new_status})
        
        