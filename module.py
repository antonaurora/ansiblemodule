#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule

def run_module():
    # 1. Определение спецификации аргументов
    module_args = dict(
        name=dict(type='str', required=True, description='Имя файла'),
        content=dict(type='str', default='', description='Содержимое файла')
    )

    # 2. Создание объекта модуля
    module = AnsibleModule(argument_spec=module_args)

    # Получаем переменные из аргументов
    file_name = module.params['name']
    content = module.params['content']
    
    changed = False
    
    try:
        # 3. Основная логика (например, создание файла)
        if not os.path.exists(file_name):
            with open(file_name, 'w') as f:
                f.write(content)
            changed = True
        else:
            # Проверка идемпотентности: если файл есть, но контент другой?
            pass 

    except Exception as e:
        module.fail_json(msg=str(e))

    # 4. Возврат результата
    module.exit_json(changed=changed, msg=f'Файл {file_name} обработан')

if __name__ == '__main__':
    run_module()
