#!/usr/bin/env python3
import json
import sys
import traceback

# Конфигурация AD
AD_SERVER = 'td-aurora.domain'
AD_USER = 'anton_adm'
AD_PASSWORD = 'pueoapcm'
BASE_DN = 'DC=td-aurora,DC=domain'
COMPUTERS_OU = 'OU=Computers,OU=AURORA,' + BASE_DN

def get_computers_from_ad():
    computers = []
    
    try:
        from ldap3 import Server, Connection, ALL
        
        server = Server(AD_SERVER, get_info=ALL)
        conn = Connection(server, AD_USER, AD_PASSWORD, auto_bind=True)
        
        conn.search(
            search_base=COMPUTERS_OU,
            search_filter='(objectClass=computer)',
            attributes=['cn', 'description', 'dNSHostName'],
            size_limit=5000
        )
        
        for entry in conn.entries:
            computer_name = str(entry.cn)
            description = str(entry.description) if entry.description else ''
            dns_hostname = str(entry.dNSHostName) if entry.dNSHostName else ''
            
            computers.append({
                'name': computer_name.lower(),
                'description': description,
                'ip': dns_hostname if dns_hostname else f"{computer_name.lower()}.{AD_SERVER}"
            })
        
        conn.unbind()
        
    except ImportError:
        pass
    except Exception as e:
        sys.stderr.write(f"AD Error: {e}\n")
      
    return computers

def build_inventory():
    computers = get_computers_from_ad()
    
    # Общие настройки для Windows хостов (SSH)
    windows_vars = {
        "ansible_connection": "ssh",
        "ansible_port": 22,
        "ansible_shell_type": "powershell",
        "ansible_ssh_common_args": "-o StrictHostKeyChecking=no",
        "ansible_host_key_checking": False,
        "ansible_user": "anton_adm",
        "ansible_password": "pueoapcm"
    }
    
    inventory = {
        "_meta": {
            "hostvars": {}
        },
        "all": {
            "hosts": [],
            "children": ["windows"]
        },
        "windows": {
            "hosts": [],
            "vars": windows_vars
        }
    }
    
    # Добавляем компьютеры из AD
    for computer in computers:
        hostname = computer['name']
        ip = computer['ip']
        description = computer.get('description', '')
        
        inventory['all']['hosts'].append(hostname)
        inventory['windows']['hosts'].append(hostname)
        
        inventory['_meta']['hostvars'][hostname] = {
            'ansible_host': ip,
            'last_user': description if description else None
        }
    
    # Добавление DC1 и DC2 с теми же настройками SSH
    dc_servers = [
        {'name': 'dc1', 'ip': '192.168.64.110'},
        {'name': 'dc2', 'ip': '192.168.64.111'},
        {'name': 'va91','ip': '192.168.64.91'}
    ]
    
    for dc in dc_servers:
        hostname = dc['name']
        ip = dc['ip']
        
        inventory['all']['hosts'].append(hostname)
        inventory['windows']['hosts'].append(hostname)
        
        inventory['_meta']['hostvars'][hostname] = {
            'ansible_host': ip,
            'ansible_connection': 'ssh',
            'ansible_port': 22,
            'ansible_shell_type': 'powershell',
            'ansible_ssh_common_args': '-o StrictHostKeyChecking=no',
            'ansible_host_key_checking': False,
            'ansible_user': 'anton_adm',
            'ansible_password': 'pueoapcm',
            'is_domain_controller': True
        }
    
    return inventory  # ← этот return должен быть внутри функции build_inventory()

def main():
    try:
        if len(sys.argv) == 2 and sys.argv[1] == '--list':
            inventory = build_inventory()
            print(json.dumps(inventory, indent=2, ensure_ascii=False))
        elif len(sys.argv) == 3 and sys.argv[1] == '--host':
            print(json.dumps({}))
        else:
            inventory = build_inventory()
            print(json.dumps(inventory, indent=2, ensure_ascii=False))
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        traceback.print_exc(file=sys.stderr)
        print(json.dumps({"_meta": {"hostvars": {}}, "all": {"hosts": []}}))

if __name__ == '__main__':
    main()
