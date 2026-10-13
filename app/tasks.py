
class TaskError(Exception):
    """任务相关的自定义异常"""
    pass


def add_task(title):
    if not isinstance(title, str):
        raise TypeError("任务标题必须是字符串")

    title = title.strip()

    if not title:
        raise TaskError("任务标题不能为空")

    task = {
        "title": title,
        "completed": False
    }

    return task


def complete_task(task):
    if not isinstance(task, dict):
        raise TypeError("任务必须是字典")

    if "completed" not in task:
        raise TaskError("任务缺少 completed 字段")

    task["completed"] = True

    return task
