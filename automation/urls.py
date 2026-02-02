from django.urls import path

from automation.views import TaskListView, TaskScheduleView

app_name = "automation"

urlpatterns = [
    path("tasks/", TaskListView.as_view(), name="task_list"),
    path("tasks/<uuid:task_id>/schedule/", TaskScheduleView.as_view(), name="task_schedule"),
]
