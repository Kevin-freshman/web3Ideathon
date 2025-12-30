from openai import OpenAI
import json

client = OpenAI(api_key="")

class ai_teach():
    def __init__(self, symbol, action, price, quantity, indicators, ability):
        self.symbol = symbol
        self.action = action
        self.price = price
        self.quantity = quantity
        self.indicators = indicators
        self.ability = ability
    def ai_interect(self):
        try:
            prompt = f"""
                你是一个量化交易领域的教育工作者，面对的是{self.ability}水平的股民。
                当前策略：{self.symbol}，动作：{self.action}, {self.price}, {self.quantity}。
                股票数据：{self.indicators}。
                请结合这些数据，用简单的语言解释为什么做出这个决策。
                """
            
            response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
            )

            semantic_json = response.choices[0].message.content
            print(semantic_json)

        except:
            print("AI模块运行异常")