with open('apps/users/assistant_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    r"f'\n> 🔧 正在调用系统工具：{display_name}...\n\n'", 
    "f'\\n> 🔧 正在调用系统工具：{display_name}...\\n\\n'"
)
content = content.replace(
    r"f'\n> 🔧 正在调用系统工具：{display_name}...\n\n'", 
    "f'\\n> 🔧 正在调用系统工具：{display_name}...\\n\\n'"
)

# Actually the string in the file is currently `f'\\n> 🔧 正在调用系统工具：{display_name}...\\n\\n'` (with double slashes)
# Let's replace `\\n` with `\n` in the string literal.
content = content.replace(
    "f'\\\\n> 🔧 正在调用系统工具：{display_name}...\\\\n\\\\n'",
    "f'\\n> 🔧 正在调用系统工具：{display_name}...\\n\\n'"
)

with open('apps/users/assistant_api.py', 'w', encoding='utf-8') as f:
    f.write(content)
