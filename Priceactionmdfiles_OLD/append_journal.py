
import sys

def append_journal_routes():
    with open('journal_routes.txt', 'r', encoding='utf-8') as src:
        content = src.read()
    
    with open('../AlgoTradingTelegramBotAndFrontend/backend/server.py', 'a', encoding='utf-8') as dst:
        dst.write('\n\n')
        dst.write(content)

if __name__ == "__main__":
    append_journal_routes()
    print("Successfully appended journal routes to server.py")
