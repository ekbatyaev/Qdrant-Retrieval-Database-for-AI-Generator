import os
from pprint import pprint

import requests
from dotenv import load_dotenv

load_dotenv()

DATABASE_API_BASE_URL = os.getenv("DATABASE_API_BASE_URL")
TOKEN = os.getenv("TOKEN", "your_secret_token")

HEADERS = {
    "token": TOKEN,
    "Content-Type": "application/json",
}


def health_check():
    response = requests.get(f"{DATABASE_API_BASE_URL}/")
    print("GET /")
    print("Status:", response.status_code)
    print("Response:", response.json())
    print("-" * 80)


def documentation_search(query, similarity, count_doc_return = 3, count_doc_rerank = 10):
    payload = {
        "query": query,
        "similarity": similarity,
        "count_doc_return": count_doc_return,
        "count_doc_rerank": count_doc_rerank,
    }

    response = requests.post(
        f"{DATABASE_API_BASE_URL}/documentation_search",
        headers=HEADERS,
        json=payload,
    )
    print("POST /documentation_search")
    print("Status:", response.status_code)
    print("Response:")
    pprint(response.json())
    print("-" * 80)


def examples_search(query, similarity, count_doc_return = 3, count_doc_rerank = 10):
    payload = {
        "query": query,
        "similarity": similarity,
        "count_doc_return": count_doc_return,
        "count_doc_rerank": count_doc_rerank,
    }

    response = requests.post(
        f"{DATABASE_API_BASE_URL}/examples_search",
        headers=HEADERS,
        json=payload,
    )
    print("POST /examples_search")
    print("Status:", response.status_code)
    print("Response:")
    pprint(response.json())
    print("-" * 80)


def documentation_add():
    payload = {
        "method_name": "player.addItem",
        "method_description": "Добавляет указанный предмет в инвентарь игрока по item_id и quantity.",
        "method_realization": """function rewardPlayer(player, item_id, quantity)
    if not player then
        return false
    end

    player:addItem(item_id, quantity)
    return true
end""",
    }

    response = requests.post(
        f"{DATABASE_API_BASE_URL}/documentation_add",
        headers=HEADERS,
        json=payload,
    )
    print("POST /documentation_add")
    print("Status:", response.status_code)
    print("Response:", response.json())
    print("-" * 80)


def examples_add():
    payload = {
        "request_text": "Как выдать игроку 5 зелий лечения после завершения квеста?",
        "request_data_example": """{
  \"player_id\": 125,
  \"item_id\": 1001,
  \"quantity\": 5,
  \"quest_id\": 77
}""",
        "request_answer_example": """local player = getPlayerById(125)
if player and isQuestCompleted(player, 77) then
    player:addItem(1001, 5)
end""",
    }

    response = requests.post(
        f"{DATABASE_API_BASE_URL}/examples_add",
        headers=HEADERS,
        json=payload,
    )
    print("POST /examples_add")
    print("Status:", response.status_code)
    print("Response:", response.json())
    print("-" * 80)


if __name__ == "__main__":
    health_check()
    # documentation_add()
    # examples_add()
    queries = [
        # """Увеличивай значение переменной try_count_n на каждой итерации
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "try_count_n": 3
        #         }
        #     }
        # }
        # """,
        #
        # """Уменьшай значение переменной retry_limit на 1 после каждой неудачной попытки
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "retry_limit": 5
        #         }
        #     }
        # }
        # """,
        #
        # """Прибавляй 2 к значению переменной current_step после выполнения шага
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "current_step": 4
        #         }
        #     }
        # }
        # """,
        #
        # """Устанавливай значение переменной attempt_number равным 1 перед первым запуском
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "attempt_number": 0
        #         }
        #     }
        # }
        # """,
        #
        # """Обнуляй значение переменной error_count после успешного завершения процесса
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "error_count": 7
        #         }
        #     }
        # }
        # """,
        #
        # """Сохраняй в переменную total_retries сумму значений retry_a и retry_b
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "retry_a": 2,
        #             "retry_b": 4,
        #             "total_retries": 0
        #         }
        #     }
        # }
        # """,
        #
        # """Увеличивай значение переменной processed_items на 10 после обработки пакета
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "processed_items": 20
        #         }
        #     }
        # }
        # """,
        #
        # """Проверяй, что переменная max_attempts больше переменной current_attempt
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "max_attempts": 8,
        #             "current_attempt": 3
        #         }
        #     }
        # }
        # """,
        #
        # """Присваивай переменной status_code значение 200 после успешного ответа
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "status_code": 0
        #         }
        #     }
        # }
        # """,
        #
        # """Записывай в переменную final_count произведение переменных part_a и part_b
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "part_a": 6,
        #             "part_b": 7,
        #             "final_count": 0
        #         }
        #     }
        # }
        # """,
        #
        # """Увеличивай значение переменной loop_index на 1 при каждом повторении цикла
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "loop_index": 9
        #         }
        #     }
        # }
        # """,
        #
        # """Сравнивай значение переменной current_value с переменной expected_value
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "current_value": 15,
        #             "expected_value": 15
        #         }
        #     }
        # }
        # """,
        #
        # """Записывай в переменную total_sum результат сложения value_x и value_y
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "value_x": 12,
        #             "value_y": 8,
        #             "total_sum": 0
        #         }
        #     }
        # }
        # """,
        #
        # """Умножай значение переменной timeout_sec на 2 при превышении лимита ожидания
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "timeout_sec": 30
        #         }
        #     }
        # }
        # """,
        #
        # """Сохраняй в переменную is_ready результат проверки, что status равен 1
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "status": 1,
        #             "is_ready": false
        #         }
        #     }
        # }
        # """,
        #
        # """Уменьшай значение переменной remaining_tasks на 1 после завершения задачи
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "remaining_tasks": 11
        #         }
        #     }
        # }
        # """,
        #
        # """Присваивай переменной batch_size значение 100 перед запуском обработки
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "batch_size": 0
        #         }
        #     }
        # }
        # """,
        #
        # """Проверяй, что переменная min_value меньше переменной max_value
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "min_value": 2,
        #             "max_value": 10
        #         }
        #     }
        # }
        # """,
        #
        # """Сохраняй в переменную diff_value разность переменных end_value и start_value
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "start_value": 14,
        #             "end_value": 25,
        #             "diff_value": 0
        #         }
        #     }
        # }
        # """,
        #
        # """Увеличивай значение переменной success_count после каждого успешного шага
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "success_count": 6
        #         }
        #     }
        # }
        # """,
        #
        # """Сохраняй в переменную average_score результат деления total_score на score_count
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "total_score": 90,
        #             "score_count": 3,
        #             "average_score": 0
        #         }
        #     }
        # }
        # """,
        #
        # """Присваивай переменной has_errors значение true, если error_count больше 0
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "error_count": 2,
        #             "has_errors": false
        #         }
        #     }
        # }
        # """,
        #
        # """Устанавливай значение переменной progress_percent равным 100 после завершения процесса
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "progress_percent": 65
        #         }
        #     }
        # }
        # """,
        #
        # """Увеличивай значение переменной page_number при переходе на следующую страницу
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "page_number": 1
        #         }
        #     }
        # }
        # """,
        #
        # """Сохраняй в переменную total_items сумму значений item_count_a и item_count_b
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "item_count_a": 17,
        #             "item_count_b": 23,
        #             "total_items": 0
        #         }
        #     }
        # }
        # """,
        #
        # """Присваивай переменной is_limit_reached значение true, если current_count больше или равен limit_count
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "current_count": 10,
        #             "limit_count": 10,
        #             "is_limit_reached": false
        #         }
        #     }
        # }
        # """,
        #
        # """Уменьшай значение переменной available_retries после каждой новой попытки
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "available_retries": 4
        #         }
        #     }
        # }
        # """,
        #
        # """Сохраняй в переменную result_code значение 500 при возникновении ошибки
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "result_code": 200
        #         }
        #     }
        # }
        # """,
        #
        # """Вычисляй значение переменной total_cost как произведение price и quantity
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "price": 150,
        #             "quantity": 3,
        #             "total_cost": 0
        #         }
        #     }
        # }
        # """,
        #
        # """Присваивай переменной is_completed значение true после успешного завершения workflow
        # Пример данных:
        # {
        #     "wf": {
        #         "vars": {
        #             "is_completed": false
        #         }
        #     }
        # }
        # """
    ]

    queries = [
        """Для полученных данных из предыдущего REST запроса очисти значения переменных ID, ENTITY_ID, CALL, вот эта: 
result = wf.vars.RESTbody.result
for _, filteredEntry in pairs(result) do
 for key, value in pairs(filteredEntry) do
 if key ~= "ID" and key ~= "ENTITY_ID" and key ~= "CALL" then
 filteredEntry[key] = nil
 end
 end
end
return result
        """
    ]
    for query in queries:

        print("QUERY:\n")
        print(query)

        documentation_search(query = query, similarity = 0.8, count_doc_return = 3, count_doc_rerank = 1)
        examples_search(query = query, similarity = 0.6, count_doc_return = 3, count_doc_rerank = 1)
