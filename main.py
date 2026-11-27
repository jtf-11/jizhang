# -*- coding: utf-8 -*-
import json
import os
import traceback
import uuid
from collections import defaultdict
from datetime import datetime, timedelta

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

Window.softinput_mode = 'below_target'

EXPENSE_CATS = ['餐饮', '交通', '购物', '居住', '娱乐', '医疗', '学习', '其他']
INCOME_CATS = ['工资', '奖金', '理财', '兼职', '红包', '其他']

RED = (0.90, 0.30, 0.30, 1)
GREEN = (0.20, 0.65, 0.35, 1)
GRAY = (0.80, 0.80, 0.80, 1)
DARK = (0.15, 0.15, 0.15, 1)
BLUE = (0.25, 0.55, 0.90, 1)


def setup_chinese_font():
    for path in (
        '/system/fonts/NotoSansCJK-Regular.ttc',
        '/system/fonts/NotoSansSC-Regular.otf',
        '/system/fonts/DroidSansFallback.ttf',
        'C:/Windows/Fonts/msyh.ttc',
        '/System/Library/Fonts/PingFang.ttc',
    ):
        if os.path.exists(path):
            try:
                LabelBase.register(name='Roboto', fn_regular=path)
                return True
            except Exception:
                pass
    return False


def _fit_text(widget, size):
    widget.text_size = (size[0], None)


class LedgerApp(App):
    def build(self):
        setup_chinese_font()
        self.title = '简易记账'
        self.data_file = os.path.join(self.user_data_dir, 'records.json')
        self.records = self._load()
        self.current_type = '支出'

        root = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))

        top = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.summary = Label(text='', font_size=sp(15), bold=True, color=DARK)
        stat_btn = Button(text='统计', font_size=sp(15), bold=True,
                          size_hint_x=None, width=dp(64),
                          background_normal='',
                          background_color=(0.30, 0.60, 0.85, 1),
                          color=(1, 1, 1, 1))
        stat_btn.bind(on_release=self.open_stat)
        top.add_widget(self.summary)
        top.add_widget(stat_btn)
        root.add_widget(top)

        row1 = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.amount_input = TextInput(hint_text='金额', input_filter='float',
                                      multiline=False, font_size=sp(17))
        self.btn_expense = Button(text='支出', font_size=sp(16), color=(1, 1, 1, 1))
        self.btn_income = Button(text='收入', font_size=sp(16), color=(1, 1, 1, 1))
        for b in (self.btn_expense, self.btn_income):
            b.background_normal = ''
            b.size_hint_x = None
            b.width = dp(64)
        self.btn_expense.bind(on_release=lambda *_: self.set_type('支出'))
        self.btn_income.bind(on_release=lambda *_: self.set_type('收入'))
        row1.add_widget(self.amount_input)
        row1.add_widget(self.btn_expense)
        row1.add_widget(self.btn_income)
        root.add_widget(row1)

        row2 = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.category = Spinner(text=EXPENSE_CATS[0], values=EXPENSE_CATS,
                                font_size=sp(16), size_hint_x=None, width=dp(110))
        self.note_input = TextInput(hint_text='备注（可选）', multiline=False,
                                    font_size=sp(16))
        row2.add_widget(self.category)
        row2.add_widget(self.note_input)
        root.add_widget(row2)

        add_btn = Button(text='添加记录', size_hint_y=None, height=dp(48),
                         font_size=sp(17), bold=True,
                         background_normal='', background_color=BLUE,
                         color=(1, 1, 1, 1))
        add_btn.bind(on_release=self.add_record)
        root.add_widget(add_btn)

        scroll = ScrollView()
        self.list_box = BoxLayout(orientation='vertical',
                                  size_hint_y=None, spacing=dp(2))
        self.list_box.bind(minimum_height=self.list_box.setter('height'))
        scroll.add_widget(self.list_box)
        root.add_widget(scroll)

        self.set_type('支出')
        self.refresh()
        return root

    # ---------- 记账交互 ----------
    def set_type(self, t):
        self.current_type = t
        if t == '支出':
            self.category.values = EXPENSE_CATS
            self.btn_expense.background_color = RED
            self.btn_income.background_color = GRAY
        else:
            self.category.values = INCOME_CATS
            self.btn_expense.background_color = GRAY
            self.btn_income.background_color = GREEN
        self.category.text = self.category.values[0]

    def add_record(self, *args):
        try:
            amount = round(float(self.amount_input.text.strip()), 2)
            if amount <= 0:
                raise ValueError
        except ValueError:
            self.toast('请输入大于 0 的金额')
            return
        now = datetime.now()
        self.records.append({
            'id': uuid.uuid4().hex,
            'type': self.current_type,
            'amount': amount,
            'category': self.category.text,
            'note': self.note_input.text.strip(),
            'date': now.strftime('%Y-%m-%d %H:%M'),
            'ts': now.timestamp(),
        })
        self._save()
        self.amount_input.text = ''
        self.note_input.text = ''
        self.refresh()

    def delete(self, rid):
        self.records = [r for r in self.records if r['id'] != rid]
        self._save()
        self.refresh()

    # ---------- 时段统计 ----------
    def open_stat(self, *args):
        today = datetime.now()
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))

        range_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
        start_input = TextInput(text=today.replace(day=1).strftime('%Y-%m-%d'),
                                multiline=False, font_size=sp(14),
                                hint_text='开始 YYYY-MM-DD')
        end_input = TextInput(text=today.strftime('%Y-%m-%d'),
                              multiline=False, font_size=sp(14),
                              hint_text='结束 YYYY-MM-DD')
        range_row.add_widget(start_input)
        range_row.add_widget(Label(text='至', size_hint_x=None, width=dp(24),
                                   font_size=sp(14), color=DARK))
        range_row.add_widget(end_input)
        content.add_widget(range_row)

        quick_row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(4))
        for label, key in (('今天', 'today'), ('本周', 'week'),
                           ('本月', 'month'), ('上月', 'last_month'),
                           ('全部', 'all')):
            b = Button(text=label, font_size=sp(13), background_normal='',
                       background_color=(0.85, 0.88, 0.95, 1), color=DARK)
            b.bind(on_release=lambda inst, k=key: self._fill_range(
                k, start_input, end_input))
            quick_row.add_widget(b)
        content.add_widget(quick_row)

        run_btn = Button(text='开始统计', size_hint_y=None, height=dp(44),
                         font_size=sp(16), bold=True, background_normal='',
                         background_color=BLUE, color=(1, 1, 1, 1))
        content.add_widget(run_btn)

        # 关键修复：用只读 TextInput 显示结果，自带滚动和自动换行
        result_input = TextInput(
            text='', readonly=True, multiline=True,
            font_size=sp(13),
            background_color=(0.97, 0.97, 0.97, 1),
            foreground_color=DARK,
        )
        content.add_widget(result_input)

        popup = Popup(title='时段统计', content=content,
                      size_hint=(0.94, 0.90), title_size=sp(17))

        def run(*_):
            try:
                text = self._compute_stat_text(start_input.text, end_input.text)
            except Exception:
                text = '统计出错：\n' + traceback.format_exc()
            result_input.text = text

        run_btn.bind(on_release=run)
        popup.open()
        # 等布局完成后自动跑一次，避免宽度为 0 时出现渲染问题
        Clock.schedule_once(run, 0.15)

    def _fill_range(self, key, start_input, end_input):
        today = datetime.now()
        if key == 'today':
            s = e = today
        elif key == 'week':
            s = today - timedelta(days=today.weekday())
            e = today
        elif key == 'month':
            s = today.replace(day=1)
            e = today
        elif key == 'last_month':
            e = today.replace(day=1) - timedelta(days=1)
            s = e.replace(day=1)
        else:
            dates = [d for d in (self._record_date(r) for r in self.records) if d]
            if dates:
                s = datetime.combine(min(dates), datetime.min.time())
                e = datetime.combine(max(dates), datetime.min.time())
            else:
                s = e = today
        start_input.text = s.strftime('%Y-%m-%d')
        end_input.text = e.strftime('%Y-%m-%d')

    @staticmethod
    def _parse_date(text):
        text = (text or '').strip().replace('/', '-').replace('.', '-')
        if not text:
            return None
        for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S'):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None

    def _record_date(self, r):
        """取记录的日期(date对象)。优先用 date 字符串，回退到时间戳。"""
        date_str = (r.get('date') or '')[:10]
        if date_str:
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        ts = r.get('ts')
        if isinstance(ts, (int, float)):
            try:
                return datetime.fromtimestamp(float(ts)).date()
            except (ValueError, OSError):
                pass
        return None

    def _compute_stat_text(self, start_text, end_text):
        s = self._parse_date(start_text)
        e = self._parse_date(end_text)
        if s is None or e is None:
            return '日期格式不对，请用 YYYY-MM-DD，例如 2026-11-01'
        s_date, e_date = s.date(), e.date()
        if s_date > e_date:
            s_date, e_date = e_date, s_date

        sel = []
        no_date = 0
        for r in self.records:
            r_date = self._record_date(r)
            if r_date is None:
                no_date += 1
                continue
            if s_date <= r_date <= e_date:
                sel.append(r)

        income = sum(float(r.get('amount', 0)) for r in sel if r.get('type') == '收入')
        expense = sum(float(r.get('amount', 0)) for r in sel if r.get('type') == '支出')

        lines = []
        lines.append('全部记录：%d 条' % len(self.records))
        lines.append('统计区间：%s ~ %s' % (s_date, e_date))
        lines.append('区间内记录：%d 条' % len(sel))
        if no_date:
            lines.append('（有 %d 条记录缺少日期，已跳过）' % no_date)
        lines.append('')
        lines.append('总收入：%.2f' % income)
        lines.append('总支出：%.2f' % expense)
        lines.append('结余：%.2f' % (income - expense))
        lines.append('')

        exp_cats = defaultdict(float)
        inc_cats = defaultdict(float)
        for r in sel:
            amt = float(r.get('amount', 0))
            cat = r.get('category', '未分类')
            if r.get('type') == '支出':
                exp_cats[cat] += amt
            else:
                inc_cats[cat] += amt

        if exp_cats:
            lines.append('【支出分类】')
            for cat, amt in sorted(exp_cats.items(), key=lambda x: -x[1]):
                lines.append('  %s   %.2f' % (cat, amt))
        if inc_cats:
            if exp_cats:
                lines.append('')
            lines.append('【收入分类】')
            for cat, amt in sorted(inc_cats.items(), key=lambda x: -x[1]):
                lines.append('  %s   %.2f' % (cat, amt))
        if not exp_cats and not inc_cats:
            lines.append('该时段没有记录。')
            lines.append('')
            lines.append('排查建议：')
            lines.append('1) 看上边「全部记录」是不是 0；')
            lines.append('2) 若全部记录>0 而区间内=0，点「全部」再统计一次；')
            lines.append('3) 若区间内=0 但日期确实覆盖今天，把这段文字发我。')

        return '\n'.join(lines)

    # ---------- 界面刷新 ----------
    def refresh(self):
        self.list_box.clear_widgets()
        income = sum(float(r.get('amount', 0)) for r in self.records if r.get('type') == '收入')
        expense = sum(float(r.get('amount', 0)) for r in self.records if r.get('type') == '支出')
        self.summary.text = '收入 %.2f   支出 %.2f   结余 %.2f' % (
            income, expense, income - expense)

        if not self.records:
            self.list_box.add_widget(
                Label(text='还没有记录，先添加一笔吧', size_hint_y=None,
                      height=dp(80), color=(0.5, 0.5, 0.5, 1)))
            return

        for r in sorted(self.records, key=lambda x: x.get('ts', 0), reverse=True):
            self.list_box.add_widget(self._row(r))

    def _row(self, r):
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        is_in = r.get('type') == '收入'
        color = GREEN if is_in else RED
        sign = '+' if is_in else '-'
        date_str = r.get('date', '')[:16]
        text = '%s  %s' % (date_str, r.get('category', ''))
        if r.get('note'):
            text += '  ' + r['note']

        left = Label(text=text, halign='left', valign='middle', font_size=sp(14))
        left.bind(size=_fit_text)
        amount = Label(text='%s%.2f' % (sign, float(r.get('amount', 0))),
                       color=color, font_size=sp(15), bold=True,
                       size_hint_x=None, width=dp(86))
        del_btn = Button(text='删', font_size=sp(13),
                         size_hint_x=None, width=dp(48),
                         background_normal='', background_color=GRAY, color=DARK)
        del_btn.bind(on_release=lambda *_: self.delete(r['id']))

        row.add_widget(left)
        row.add_widget(amount)
        row.add_widget(del_btn)
        return row

    # ---------- 存储 ----------
    def _load(self):
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.toast('保存失败：%s' % e)

    def toast(self, msg):
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content.add_widget(Label(text=msg, font_size=sp(15)))
        ok = Button(text='好', size_hint_y=None, height=dp(44))
        content.add_widget(ok)
        popup = Popup(title='提示', content=content,
                      size_hint=(0.8, 0.35), title_size=sp(16))
        ok.bind(on_release=popup.dismiss)
        popup.open()


if __name__ == '__main__':
    LedgerApp().run()