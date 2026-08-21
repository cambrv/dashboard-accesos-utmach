import re
import os

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace specific emojis and known patterns without breaking code
emoji_pattern = re.compile(r'[\U0001F300-\U0001F9FF\U00002600-\U000027FF]')
content = emoji_pattern.sub('', content)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Emojis removed.")
