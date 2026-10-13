
from app.tasks import (
    add_task,
    complete_task,
    TaskError
)


def main():
    titles = [
        "学习 Python 异常处理",
        "",
        123,
        "   学习 FastAPI   "
    ]

    for title in titles:
        try:
            task = add_task(title)
            complete_task(task)

        except TaskError as e:
            print("业务错误：", e)

        except TypeError as e:
            print("类型错误：", e)

        else:
            print("任务创建并完成：", task)

        finally:
            print("本次任务处理结束")
            print("-" * 30)


if __name__ == "__main__":
    main()
