from feedcollector import FeedCollector
import asyncio
from logger import PM
import uuid
from datetime import datetime

def save_to_test_file(html_content):
    testdir = PM.base_path / "test"
    testdir.mkdir(parents=True, exist_ok=True)
    filename = testdir / f"test_{PM.today_format()}_{(uuid.uuid4().hex)[:8]}.html"  
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)

async def many_feed():
    collector = FeedCollector(cfg=FeedCollector._TEST)
    all_data = await collector.collect_all()
    html_content = collector.generate_email_html(all_data)
    return html_content

if __name__ == "__main__":
    html_content = asyncio.run(many_feed())
    save_to_test_file(html_content)
        