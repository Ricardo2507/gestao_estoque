from django.urls import path
from . import views

app_name = "estoque_inteligente"

urlpatterns = [
    path("", views.RelatorioListView.as_view(), name="relatorio_list"),
    path("upload/", views.RelatorioUploadView.as_view(), name="relatorio_upload"),
    path("relatorios/<int:pk>/", views.RelatorioDetailView.as_view(),
         name="relatorio_detail"),
    path(
        "relatorios/<int:pk>/processar/",
        views.processar_itens_relatorio,
        name="relatorio_processar",
    ),
    path(
        "relatorios/<int:pk>/excluir/",
        views.RelatorioDeleteView.as_view(),
        name="relatorio_delete",
    ),
]
