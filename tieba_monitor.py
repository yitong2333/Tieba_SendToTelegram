import asyncio
import requests
from aiotieba import Client
from dotenv import load_dotenv
import os
from datetime import datetime

# 加载环境变量
load_dotenv()

async def get_latest_floor(client, tid):
    try:
        # 获取第一页的帖子内容，包含总页数
        posts = await client.get_posts(tid, pn=1)

        if not posts:
            print("未能获取到帖子内容")
            return None, None, None, None, None

        # 获取总页数
        total_pages = posts.page.total_page

        # 获取最新一页的帖子内容
        latest_posts = await client.get_posts(tid, pn=total_pages)

        if not latest_posts:
            print("未能获取到帖子内容")
            return None, None, None, None, None

        # 获取最新的楼层信息
        latest_post = latest_posts[-1]
        latest_floor_content = latest_post.text
        latest_floor_author_id = latest_post.author_id
        latest_floor_author_ip = latest_post.user.ip
        latest_floor_time = datetime.fromtimestamp(latest_post.create_time).strftime('%Y-%m-%d %H:%M:%S')
        latest_floor_link = f"https://tieba.baidu.com/p/{tid}?pid={latest_post.pid}&cid=0#{latest_post.pid}"

        # 通过author_id获取作者信息
        author_info = await client.get_user_info(latest_floor_author_id)
        latest_floor_author = author_info.user_name  # 获取用户名

        return latest_post, latest_floor_author, latest_floor_content, latest_floor_author_ip, latest_floor_time, latest_floor_link
    except Exception as e:
        print(f"获取最新楼层时发生错误: {e}")
        return None, None, None, None, None

def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        print("消息发送成功")
    else:
        print(f"消息发送失败，状态码：{response.status_code}, 返回内容：{response.text}")

async def main():
    # 从环境变量中获取BDUSS、帖子ID和Telegram信息
    bduss = os.getenv('BDUSS')
    tid = int(os.getenv('TID'))
    telegram_token = os.getenv('TELEGRAM_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    keywords_env = os.getenv('KEYWORDS')
    keywords = keywords_env.split(',') if keywords_env else []

    if not (bduss and tid and telegram_token and telegram_chat_id):
        print("环境变量未正确加载")
        return

    # 使用BDUSS初始化Client
    async with Client(BDUSS=bduss) as client:
        last_pid = None

        while True:
            try:
                latest_post, author, content, ip, post_time, post_link = await get_latest_floor(client, tid)
                if latest_post and author and content:
                    print(f"获取到最新楼层: pid={latest_post.pid}, content={content}")
                    if last_pid != latest_post.pid:
                        print(f"检测到新楼层: pid={latest_post.pid}")
                        last_pid = latest_post.pid
                        if keywords or any(keyword in content for keyword in keywords):
                            message = f"{content}\n\n\n👩‍💻 发布人: {author}\n🌏 IP: {ip}\n🕔 时间: {post_time}\n🔗 跳转链接: [点此跳转]({post_link})"
                            print("发送消息到Telegram: ", message)
                            send_telegram_message(telegram_token, telegram_chat_id, message)  # 发送到Telegram
                    else:
                        print("楼层内容未更新")
                else:
                    print("未能获取到最新楼层内容")

                # 等待一段时间再检查
                await asyncio.sleep(30)

            except asyncio.CancelledError:
                print("程序被中断")
                break
            except Exception as e:
                print(f"主循环中发生错误: {e}")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("程序手动终止")
