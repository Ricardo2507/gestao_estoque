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
    path(
        "consumo-ur/",
        views.ConsumoURListView.as_view(),
        name="consumo_ur_list",
    ),
    path(
        "consumo-ur/upload/",
        views.ConsumoURUploadView.as_view(),
        name="consumo_ur_upload",
    ),
    path(
        "consumo-ur/<int:pk>/",
        views.ConsumoURDetailView.as_view(),
        name="consumo_ur_detail",
    ),
    path(
        "consumo-ur/<int:pk>/excluir/",
        views.ConsumoURDeleteView.as_view(),
        name="consumo_ur_delete",
    ),
    path(
    "consumo-material/",
    views.ConsumoMaterialListView.as_view(),
    name="consumo_material_list",
    ),
    path(
        "consumo-material/upload/",
        views.ConsumoMaterialUploadView.as_view(),
        name="consumo_material_upload",
    ),
    path(
        "consumo-material/<int:pk>/",
        views.ConsumoMaterialDetailView.as_view(),
        name="consumo_material_detail",
    ),
    path(
        "consumo-material/<int:pk>/excluir/",
        views.ConsumoMaterialDeleteView.as_view(),
        name="consumo_material_delete",
    ),
]
