import sys

def append_to_file():
    with open('pa_routes.txt', 'r', encoding='utf-8') as src:
        content = src.read()
    
    with open('../AlgoTradingTelegramBotAndFrontend/backend/server.py', 'a', encoding='utf-8') as dst:
        dst.write('\n\n')
        dst.write(content)

if __name__ == "__main__":
    append_to_file()
    print("Successfully appended routes to server.py")
