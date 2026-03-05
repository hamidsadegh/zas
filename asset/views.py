import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, UpdateView

from openpyxl import Workbook

from asset.forms import InventoryItemForm
from asset.models import InventoryItem
from dcim.models import Site


PER_PAGE_OPTIONS = (10, 25, 50, 100, 200)
QUICK_FILTER_PARAMS = (
    "qf_designation",
    "qf_inventory_number",
    "qf_serial_number",
    "qf_location",
    "qf_vendor",
    "qf_model",
    "qf_item_type",
    "qf_status",
    "qf_comment",
)


def _natural_sort_key(value):
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", value or "")
    ]


def _get_paginate_by(request, default=25):
    per_page = request.GET.get("paginate_by")
    if per_page and per_page.isdigit():
        per_page = int(per_page)
        if per_page in PER_PAGE_OPTIONS:
            return per_page
    return default


def _contains(value, query):
    return query.lower() in (value or "").lower()


def _storage_site_choices():
    choices = [("all", "All Sites")]
    for site in Site.objects.order_by("name"):
        choices.append((str(site.id), site.name))
    return choices


def _storage_quick_filter_values(request):
    return {
        key: request.GET.get(key, "").strip()
        for key in QUICK_FILTER_PARAMS
    }


def _build_storage_rows(search_query):
    queryset = (
        InventoryItem.objects.select_related("vendor", "site", "area")
        .all()
    )

    query = (search_query or "").lower().strip()
    rows = []

    for item in queryset:
        location = str(item.area) if item.area else item.site.name if item.site else ""
        haystack = " ".join(
            filter(
                None,
                [
                    item.designation,
                    item.inventory_number or "",
                    item.serial_number or "",
                    item.vendor.name if item.vendor else "",
                    item.model,
                    item.site.name if item.site else "",
                    str(item.area) if item.area else "",
                    item.get_item_type_display(),
                    item.get_status_display(),
                    item.comment or "",
                ],
            )
        ).lower()
        if query and query not in haystack:
            continue

        rows.append(
            {
                "item": item,
                "designation": item.designation or "",
                "inventory_number": item.inventory_number or "",
                "serial_number": item.serial_number or "",
                "location": location,
                "vendor_name": item.vendor.name if item.vendor else "",
                "model": item.model or "",
                "item_type": item.get_item_type_display(),
                "status": item.get_status_display(),
                "comment": item.comment or "",
                "site_id": str(item.site.id) if item.site else "",
            }
        )

    return rows


def _sort_storage_rows(rows, sort_field):
    reverse = False
    field = sort_field or "designation"
    if field.startswith("-"):
        reverse = True
        field = field[1:]

    sort_keys = {
        "designation": lambda row: _natural_sort_key(row["designation"]),
        "inventory_number": lambda row: _natural_sort_key(row["inventory_number"]),
        "serial_number": lambda row: str(row["serial_number"]).lower(),
        "location": lambda row: _natural_sort_key(row["location"]),
        "vendor_name": lambda row: _natural_sort_key(row["vendor_name"]),
        "model": lambda row: _natural_sort_key(row["model"]),
        "item_type": lambda row: _natural_sort_key(row["item_type"]),
        "status": lambda row: _natural_sort_key(row["status"]),
        "comment": lambda row: str(row["comment"]).lower(),
    }

    sort_key = sort_keys.get(field, sort_keys["designation"])
    rows.sort(key=sort_key, reverse=reverse)
    return rows


def _storage_view_data(request):
    search_query = request.GET.get("search", "").strip()
    sort_field = request.GET.get("sort", "designation")
    quick_filter_values = _storage_quick_filter_values(request)

    site_choices = _storage_site_choices()
    site_filter = request.GET.get("site", "all")
    valid_site_keys = {choice[0] for choice in site_choices}
    if site_filter not in valid_site_keys:
        site_filter = "all"

    rows = _build_storage_rows(search_query)

    if site_filter != "all":
        rows = [row for row in rows if row["site_id"] == site_filter]

    if quick_filter_values["qf_designation"]:
        rows = [
            row
            for row in rows
            if _contains(row["designation"], quick_filter_values["qf_designation"])
        ]
    if quick_filter_values["qf_inventory_number"]:
        rows = [
            row
            for row in rows
            if _contains(
                row["inventory_number"], quick_filter_values["qf_inventory_number"]
            )
        ]
    if quick_filter_values["qf_serial_number"]:
        rows = [
            row
            for row in rows
            if _contains(row["serial_number"], quick_filter_values["qf_serial_number"])
        ]
    if quick_filter_values["qf_location"]:
        rows = [
            row
            for row in rows
            if _contains(row["location"], quick_filter_values["qf_location"])
        ]
    if quick_filter_values["qf_vendor"]:
        rows = [
            row
            for row in rows
            if _contains(row["vendor_name"], quick_filter_values["qf_vendor"])
        ]
    if quick_filter_values["qf_model"]:
        rows = [
            row
            for row in rows
            if _contains(row["model"], quick_filter_values["qf_model"])
        ]
    if quick_filter_values["qf_item_type"]:
        rows = [
            row
            for row in rows
            if _contains(row["item_type"], quick_filter_values["qf_item_type"])
        ]
    if quick_filter_values["qf_status"]:
        rows = [
            row
            for row in rows
            if _contains(row["status"], quick_filter_values["qf_status"])
        ]
    if quick_filter_values["qf_comment"]:
        rows = [
            row
            for row in rows
            if _contains(row["comment"], quick_filter_values["qf_comment"])
        ]

    rows = _sort_storage_rows(rows, sort_field)

    return {
        "rows": rows,
        "search_query": search_query,
        "sort_field": sort_field,
        "site_choices": site_choices,
        "site_filter": site_filter,
        "quick_filter_values": quick_filter_values,
    }


@login_required
def storage_inventory_list(request):
    view_data = _storage_view_data(request)
    paginate_by = _get_paginate_by(request, default=50)
    paginator = Paginator(view_data["rows"], paginate_by)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        **view_data,
        "rows": page_obj,
        "paginate_by": paginate_by,
        "per_page_options": PER_PAGE_OPTIONS,
    }
    return render(request, "asset/storage_inventory.html", context)


@login_required
def storage_inventory_export(request):
    view_data = _storage_view_data(request)
    rows = view_data["rows"]

    wb = Workbook()
    ws = wb.active
    ws.title = "Storage Inventory"
    headers = [
        "Designation",
        "Inventory Number",
        "Serial Number",
        "Location",
        "Vendor",
        "Model",
        "Item Type",
        "Status",
        "Comment",
    ]
    ws.append(headers)

    for row in rows:
        ws.append(
            [
                row["designation"],
                row["inventory_number"],
                row["serial_number"],
                row["location"],
                row["vendor_name"],
                row["model"],
                row["item_type"],
                row["status"],
                row["comment"],
            ]
        )

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        'attachment; filename="storage-inventory.xlsx"'
    )
    wb.save(response)
    return response


class InventoryItemAddView(LoginRequiredMixin, CreateView):
    model = InventoryItem
    form_class = InventoryItemForm
    template_name = "asset/storage_inventory_form.html"
    success_url = reverse_lazy("inventory_storage")

    def form_valid(self, form):
        messages.success(self.request, "Storage inventory item created successfully.")
        return super().form_valid(form)


class InventoryItemUpdateView(LoginRequiredMixin, UpdateView):
    model = InventoryItem
    form_class = InventoryItemForm
    template_name = "asset/storage_inventory_form.html"
    success_url = reverse_lazy("inventory_storage")

    def form_valid(self, form):
        messages.success(self.request, "Storage inventory item updated successfully.")
        return super().form_valid(form)


class InventoryItemDeleteView(LoginRequiredMixin, DeleteView):
    model = InventoryItem
    template_name = "asset/storage_inventory_confirm_delete.html"
    success_url = reverse_lazy("inventory_storage")

    def form_valid(self, form):
        messages.success(self.request, "Storage inventory item deleted.")
        return super().form_valid(form)
