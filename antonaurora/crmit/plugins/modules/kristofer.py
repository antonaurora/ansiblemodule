#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
- name: Получить задачу
  antonaurora.crmit.kristofer:
    connection_params: "{{ conn_mysql }}"
    action: view
  register: task



- name: Обработать задачу
  block:
    - name: Добавить комментарий
      antonaurora.crmit.kristofer:
        connection_params: "{{ conn_mysql }}"
        action: comment
        task_id: "{{ task.task.id }}"
        comment: "Права успешно настроены"

    - name: Закрыть задачу
      antonaurora.crmit.kristofer:
        connection_params: "{{ conn_mysql }}"
        action: close
        task_id: "{{ task.task.id }}"
  when: task.task_found
"""

from ansible.module_utils.basic import AnsibleModule
import pymysql

try:
    import pymysql
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False

# SQL запрос для просмотра задачи
TASK_VIEW = """
SELECT 
    u.login,
    u.workplace,
    CASE 
        WHEN bt.task_type IN ('user_permission_removal', 'position_permission_removal') THEN 'remove'
        WHEN bt.task_type IN ('user_permission', 'position_permission') THEN 'add'
        ELSE bt.status
    END AS state,
    p.code AS folder,
    bt.id
FROM backlog_tasks bt
LEFT JOIN users u ON bt.user_id = u.id
LEFT JOIN permissions p ON bt.permission_id = p.id
WHERE bt.user_id IS NOT NULL 
    AND bt.executor_id = 2
    AND bt.status = 'in_progress'
    AND p.module = 'ДИСК'
ORDER BY bt.assigned_at
LIMIT 1
"""

# SQL запрос для закрытия задачи
TASK_CLOSE = """
UPDATE backlog_tasks 
SET status = 'completed'
WHERE id = %s
"""

# SQL запрос для добавления комментария
TASK_COMMENT = """
UPDATE backlog_tasks 
SET comments = %s
WHERE id = %s
"""

def view_task(connection, module, result):
    """Функция для просмотра активной задачи"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(TASK_VIEW)
            tasks = cursor.fetchall()

            if tasks and len(tasks) > 0:
                task = tasks[0]
                result['task_found'] = True
                result['task'] = {
                    'login': task.get('login'),
                    'workplace': task.get('workplace'),
                    'state': task.get('state'),
                    'folder': task.get('folder'),
                    'id': task.get('id')
                }
                result['message'] = f"Найдена задача: {task.get('login')} - {task.get('state')} - {task.get('folder')}"
                result['task_id'] = task.get('id')
            else:
                result['message'] = "Задач нет."
                result['task_found'] = False
                
    except Exception as e:
        module.fail_json(
            msg=f"Ошибка выполнения запроса TASK_VIEW: {str(e)}",
            **result
        )
    
    return result

def close_task(connection, module, result, task_id):
    """Функция для закрытия задачи по ID"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(TASK_CLOSE, (task_id,))
            connection.commit()
            
            if cursor.rowcount > 0:
                result['changed'] = True
                result['task_closed'] = True
                result['message'] = f"Задача с ID {task_id} успешно закрыта"
            else:
                result['task_closed'] = False
                result['message'] = f"Задача с ID {task_id} не найдена или уже закрыта"
                
    except Exception as e:
        connection.rollback()
        module.fail_json(
            msg=f"Ошибка при закрытии задачи: {str(e)}",
            **result
        )
    
    return result

def add_comment(connection, module, result, task_id, comment):
    """Функция для добавления комментария к задаче"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(TASK_COMMENT, (comment, task_id))
            connection.commit()
            
            if cursor.rowcount > 0:
                result['changed'] = True
                result['comment_added'] = True
                result['message'] = f"Комментарий добавлен к задаче {task_id}"
            else:
                result['comment_added'] = False
                result['message'] = f"Задача {task_id} не найдена"
                
    except Exception as e:
        connection.rollback()
        module.fail_json(
            msg=f"Ошибка при добавлении комментария: {str(e)}",
            **result
        )
    
    return result

def main():
    module_args = dict(
        connection_params=dict(
            type='dict',
            required=True,
            options=dict(
                mysql_host=dict(type='str', required=True),
                mysql_user=dict(type='str', required=True),
                mysql_password=dict(type='str', required=True, no_log=True),
                mysql_database=dict(type='str', required=True)
            )
        ),
        action=dict(type='str', required=False, default='view', choices=['view', 'close', 'comment']),
        task_id=dict(type='int', required=False),
        comment=dict(type='str', required=False)
    )
    
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        required_if=[
            ('action', 'close', ['task_id']),
            ('action', 'comment', ['task_id', 'comment'])
        ]
    )
    
    # Проверяем наличие pymysql
    if not HAS_PYMYSQL:
        module.fail_json(msg="pymysql не установлен. Установите: pip install pymysql")
    
    result = {
        'changed': False,
        'task_found': False,
        'task_closed': False,
        'comment_added': False,
        'task': None,
        'task_id': None,
        'message': '',
        'action': module.params['action']
    }
    
    # Подключаемся к MySQL
    connection = None
    try:
        connection = pymysql.connect(
            host=module.params['connection_params']['mysql_host'],
            user=module.params['connection_params']['mysql_user'],
            password=module.params['connection_params']['mysql_password'],
            database=module.params['connection_params']['mysql_database'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        module.fail_json(
            msg=f"Ошибка подключения к MySQL: {str(e)}",
            **result
        )
    
    # Выполняем действие
    try:
        if module.params['action'] == 'view':
            result = view_task(connection, module, result)
        elif module.params['action'] == 'close':
            result = close_task(connection, module, result, module.params['task_id'])
        elif module.params['action'] == 'comment':
            result = add_comment(connection, module, result, module.params['task_id'], module.params['comment'])
    finally:
        if connection:
            connection.close()
    
    module.exit_json(**result)

if __name__ == '__main__':
    main()
