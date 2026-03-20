#!pip install discord.py
#!pip install openai discord.py nest_asyncio
#pip install boto3

import discord
from discord.ext import commands
import json
import boto3

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# 建議使用環境變數或設定檔，不要直接寫在程式碼中
DISCORD_TOKEN = "自己找"
AWS_KEY = "自己打"
AWS_SECRET = "自己打"


@bot.event
async def on_message(message):
    # 如果訊息是機器人自己發的，就忽略
    if message.author == bot.user:
        return

    # 檢查機器人是否被標記 (@)
    if bot.user.mentioned_in(message):
        # 取得標記後的文字內容 (移除標記部分)
        question = message.content.replace(f'<@{bot.user.id}>', '').strip()

        if not question:
            await message.channel.send("找我有事嗎？請在標記我後輸入問題喔！")
            return

        # 這裡直接呼叫你原本寫好的 ai 指令邏輯
        ctx = await bot.get_context(message)
        await ctx.invoke(ai, question=question)

    # 確保原本的指令 (!ai) 還能運作
    await bot.process_commands(message)




bedrock = boto3.client(
    "bedrock-runtime",
    region_name="us-east-1",
    aws_access_key_id=AWS_KEY,
    aws_secret_access_key=AWS_SECRET
)

MODEL_ID = "amazon.nova-lite-v1:0"


# 1. 原有的 AI 指令 (稍微優化了解析邏輯與打字狀態)
@bot.command()
async def ai(ctx, *, question):
    # 顯示「正在輸入中...」
    async with ctx.typing():
        try:
            body = json.dumps({
                "system": [{"text": "你是一個專業無所不能，且富有幽默感的助手，請使用繁體中文回答。"}],
                "messages": [{"role": "user", "content": [{"text": question}]}],
                "inferenceConfig": {"max_new_tokens": 1000, "temperature": 0.7}
            })

            response = bedrock.invoke_model(
                modelId=MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=body
            )

            response_body = json.loads(response["body"].read())
            answer = response_body["output"]["message"]["content"][0]["text"]
            await ctx.reply(answer) # 使用 reply 會標註使用者，比較親切

        except Exception as e:
            print(f"Error: {e}")
            await ctx.send(f"發生錯誤: {str(e)}")

# 2. 新增的監聽事件：處理「標記 @」的行為
@bot.event
async def on_message(message):
    # 判斷一：如果是機器人自己說話，不理會
    if message.author == bot.user:
        return

    # 判斷二：如果機器人被標記了 (@機器人)
    if bot.user.mentioned_in(message):
        # 清除訊息中的標記標籤，只留下純文字問題
        clean_content = message.content.replace(f'<@{bot.user.id}>', '').strip()
        clean_content = clean_content.replace(f'<@!{bot.user.id}>', '').strip() # 考慮部分客戶端的標籤差異

        if clean_content:
            # 手動觸發上面定義好的 ai 指令
            ctx = await bot.get_context(message)
            await ctx.invoke(ai, question=clean_content)
        else:
            await message.channel.send(f"找我有事嗎？ {message.author.mention} 請在標記我後輸入問題喔！")
            return

    # 判斷三：這行非常重要！沒有它，原本的 !ai 指令會失效
    await bot.process_commands(message)

# 3. 最後才是啟動 (這行永遠放在最後)
bot.run(DISCORD_TOKEN)
