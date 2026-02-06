#!/usr/bin/env python3
import requests
import subprocess
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
import os
import time
from datetime import datetime

API_URL = "https://print.lukasreis.com/api/messages"
PRINTED_FILE = "/home/printer/printed.txt"
POLL_INTERVAL = 10

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 15 * mm
COL_GAP = 10 * mm
COL_WIDTH = (PAGE_WIDTH - 2 * MARGIN - COL_GAP) / 2
LINE_HEIGHT = 12
HEADER_HEIGHT = 25
FOOTER_HEIGHT = 20

last_count = 0

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def get_printed_ids():
    if os.path.exists(PRINTED_FILE):
        with open(PRINTED_FILE) as f:
            return set(int(x.strip()) for x in f if x.strip())
    return set()

def save_printed_ids(ids):
    with open(PRINTED_FILE, "a") as f:
        for msg_id in ids:
            f.write(f"{msg_id}\n")

def wrap_text(text, max_width):
    lines = []
    for paragraph in text.split('\n'):
        words = paragraph.split(' ')
        current_line = ''
        for word in words:
            while stringWidth(word, 'Helvetica', 9) > max_width:
                for i in range(len(word), 0, -1):
                    if stringWidth(word[:i], 'Helvetica', 9) <= max_width:
                        if current_line:
                            lines.append(current_line)
                            current_line = ''
                        lines.append(word[:i])
                        word = word[i:]
                        break
                else:
                    break
            test_line = f"{current_line} {word}".strip() if current_line else word
            if stringWidth(test_line, 'Helvetica', 9) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        if not paragraph:
            lines.append('')
    return lines

def get_message_height(msg):
    lines = wrap_text(msg.get('message') or '', COL_WIDTH - 5)
    return 20 + len(lines) * LINE_HEIGHT + 20

def draw_header(c):
    y = PAGE_HEIGHT - MARGIN
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGIN, y, "messages")
    c.setFont("Helvetica", 10)
    c.drawRightString(PAGE_WIDTH - MARGIN, y, "print.lukasreis.com")
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.line(MARGIN, y - 10, PAGE_WIDTH - MARGIN, y - 10)

def draw_footer(c):
    y = MARGIN
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.line(MARGIN, y + 10, PAGE_WIDTH - MARGIN, y + 10)
    c.setFont("Helvetica", 9)
    c.drawCentredString(PAGE_WIDTH / 2, y, "Made by Lukas with <3")

def draw_message(c, msg, x, y):
    name = (msg.get('name') or 'Anonymous')[:25]
    date = msg.get('created_at', '')[:10]
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, name)
    c.setFont("Helvetica", 8)
    c.drawRightString(x + COL_WIDTH - 5, y, date)
    c.setFont("Helvetica", 9)
    lines = wrap_text(msg.get('message') or '', COL_WIDTH - 5)
    text_y = y - 15
    for line in lines:
        c.drawString(x, text_y, line)
        text_y -= LINE_HEIGHT
    line_y = text_y - 8
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.line(x, line_y, x + COL_WIDTH - 5, line_y)
    return line_y - 10

def create_pdf(messages, filename="/tmp/messages.pdf"):
    c = canvas.Canvas(filename, pagesize=A4)
    col_positions = [MARGIN, MARGIN + COL_WIDTH + COL_GAP]
    start_y = PAGE_HEIGHT - MARGIN - HEADER_HEIGHT
    min_y = MARGIN + FOOTER_HEIGHT
    col_y = [start_y, start_y]
    col = 0
    draw_header(c)
    for msg in messages:
        height = get_message_height(msg)
        if col_y[col] - height < min_y:
            if col == 0:
                col = 1
            else:
                draw_footer(c)
                c.showPage()
                draw_header(c)
                col_y = [start_y, start_y]
                col = 0
        if col_y[col] - height < min_y:
            col = 1
        col_y[col] = draw_message(c, msg, col_positions[col], col_y[col])
    draw_footer(c)
    c.save()
    return filename

def print_pdf(filepath):
    subprocess.run(["lp", filepath])

def check_and_print():
    global last_count
    try:
        printed = get_printed_ids()
        messages = requests.get(API_URL, timeout=5).json()
        new_messages = [m for m in messages if m['id'] not in printed]
        new_messages = sorted(new_messages, key=lambda m: m['id'])

        if len(new_messages) > last_count:
            for msg in new_messages[last_count:]:
                name = (msg.get('name') or 'Anon')[:20]
                log(f"new: #{msg['id']} from {name}")
        last_count = len(new_messages)

        if not new_messages:
            return None

        total_height = sum(get_message_height(m) for m in new_messages)
        page_capacity = (PAGE_HEIGHT - 2 * MARGIN - HEADER_HEIGHT - FOOTER_HEIGHT) * 2
        pct = int(total_height / page_capacity * 100)

        if total_height >= page_capacity:
            height_acc = 0
            cut_idx = len(new_messages)
            for i, msg in enumerate(new_messages):
                height_acc += get_message_height(msg)
                if height_acc >= page_capacity:
                    cut_idx = i + 1
                    break

            to_print = new_messages[:cut_idx]
            pdf = create_pdf(to_print)
            print_pdf(pdf)
            save_printed_ids([m['id'] for m in to_print])
            last_count = 0
            return f"printed {len(to_print)} messages"
        else:
            return f"{len(new_messages)} msgs ({pct}% full)"
    except Exception as e:
        return f"error: {e}"

def main():
    log("print daemon started")
    log(f"polling {API_URL} every {POLL_INTERVAL}s")
    while True:
        result = check_and_print()
        if result:
            log(result)
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
