from rest_framework.permissions import BasePermission

class IsSupplier(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'supplier'


class IsSupplierStaff(BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ['supplier', 'sales_rep']

class IsClient(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'client'
    
