from django.urls import path
from .views import (
    ExpenseListCreateView, ExpenseDetailView,
    WorkerBonusListCreateView, WorkerBonusDetailView,
    FinanceSummaryView,
)

urlpatterns = [
    path('summary/', FinanceSummaryView.as_view()),
    path('expenses/', ExpenseListCreateView.as_view()),
    path('expenses/<int:pk>/', ExpenseDetailView.as_view()),
    path('bonuses/', WorkerBonusListCreateView.as_view()),
    path('bonuses/<int:pk>/', WorkerBonusDetailView.as_view()),
]