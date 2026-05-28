import sys
import json
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMenu, QFrame
)
from PyQt5.QtCore import Qt


class TodoItem(QFrame):
    """自定义清单项组件"""

    def __init__(self, text, is_done=False, parent_list_item=None, state_callback=None):
        super().__init__()
        self.parent_list_item = parent_list_item
        self.state_callback = state_callback

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)

        # 1. 复选框
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(is_done)
        self.checkbox.stateChanged.connect(self.on_state_change)

        # 2. 文本显示标签
        self.label = QLabel(text)
        self.label.setStyleSheet("color: white; font-family: 'Microsoft YaHei';")

        # 3. 内联编辑框，默认隐藏
        self.edit_line = QLineEdit(text)
        self.edit_line.setStyleSheet("""
            background: rgba(255, 255, 255, 40); 
            border: 1px solid rgba(255, 255, 255, 80);
            border-radius: 4px; 
            color: white; 
            padding: 2px;
        """)
        self.edit_line.hide()
        self.edit_line.editingFinished.connect(self.finish_edit)

        layout.addWidget(self.checkbox)
        layout.addWidget(self.label)
        layout.addWidget(self.edit_line)
        layout.addStretch()

        self.update_style(self.checkbox.checkState())

    def mouseDoubleClickEvent(self, event):
        """双击触发编辑"""
        if event.button() == Qt.LeftButton:
            self.start_edit()
        super().mouseDoubleClickEvent(event)

    def start_edit(self):
        """进入编辑模式"""
        self.label.hide()
        self.edit_line.setText(self.label.text())
        self.edit_line.show()
        self.edit_line.setFocus()
        self.edit_line.selectAll()

    def finish_edit(self):
        """完成编辑"""
        if self.edit_line.isHidden():
            return

        new_text = self.edit_line.text().strip()
        if new_text:
            self.label.setText(new_text)

        self.edit_line.hide()
        self.label.show()

        if self.state_callback:
            self.state_callback()

    def on_state_change(self, state):
        """复选框状态变化"""
        self.update_style(state)

        if self.state_callback:
            self.state_callback()

    def update_style(self, state):
        """根据任务状态更新样式"""
        if state == Qt.Checked:
            self.label.setStyleSheet(
                "color: #888; "
                "font-family: 'Microsoft YaHei'; "
                "text-decoration: line-through;"
            )
        else:
            self.label.setStyleSheet(
                "color: white; "
                "font-family: 'Microsoft YaHei';"
            )


class DesktopTodo(QWidget):
    def __init__(self):
        super().__init__()

        self.data_file = "todo_data.json"
        self.hide_completed = False

        # 桌面小组件窗口样式
        self.setWindowFlags(Qt.WindowFlags(0x00000800 | 0x04000000 | 0x0000000a))
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.initUI()
        self.load_data()
        self.resize(300, 450)

    def initUI(self):
        self.setStyleSheet("""
            QWidget#MainContainer {
                background-color: rgba(30, 30, 30, 180);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 30);
            }
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item:selected {
                background: rgba(255, 255, 255, 20);
                border-radius: 4px;
            }
            QLineEdit {
                background: rgba(255, 255, 255, 40);
                border: none;
                border-radius: 4px;
                color: white;
                padding: 5px;
            }
        """)

        self.main_layout = QVBoxLayout(self)

        self.container = QWidget()
        self.container.setObjectName("MainContainer")
        self.container_layout = QVBoxLayout(self.container)

        self.title = QLabel("📝 Todo")
        self.title.setStyleSheet(
            "color: #00d4ff; "
            "font-weight: bold; "
            "font-size: 16px; "
            "margin: 5px;"
        )
        self.container_layout.addWidget(self.title)

        self.list_widget = QListWidget()
        self.container_layout.addWidget(self.list_widget)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("输入任务并回车...")
        self.input_field.returnPressed.connect(self.add_task)
        self.input_field.hide()
        self.container_layout.addWidget(self.input_field)

        self.main_layout.addWidget(self.container)

    def create_task_item(self, text, is_done=False):
        """创建任务项"""
        item = QListWidgetItem()
        todo_widget = TodoItem(
            text=text,
            is_done=is_done,
            parent_list_item=item,
            state_callback=self.on_task_state_changed
        )

        item.setSizeHint(todo_widget.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, todo_widget)

    def collect_tasks(self):
        """收集当前所有任务数据"""
        data = []

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)

            if widget:
                data.append({
                    "text": widget.label.text(),
                    "done": widget.checkbox.isChecked()
                })

        return data

    def reorder_tasks(self):
        """未完成任务在上，已完成任务在下"""
        data = self.collect_tasks()

        # False 在前，True 在后
        # sort 是稳定排序，不会打乱同类任务的原始顺序
        data.sort(key=lambda x: x["done"])

        self.list_widget.clear()

        for entry in data:
            self.create_task_item(entry["text"], entry["done"])

    def add_task(self, text=None, is_done=False):
        """添加任务"""
        content = text if text else self.input_field.text().strip()

        if content:
            self.create_task_item(content, is_done)

            self.input_field.clear()
            self.input_field.hide()

            self.reorder_tasks()
            self.save_data()
            self.apply_visibility_logic()

    def on_task_state_changed(self):
        """任务状态变化后自动排序"""
        self.reorder_tasks()
        self.save_data()
        self.apply_visibility_logic()

    def apply_visibility_logic(self):
        """隐藏或显示已完成任务"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)

            if widget:
                if self.hide_completed and widget.checkbox.isChecked():
                    item.setHidden(True)
                else:
                    item.setHidden(False)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #333;
                color: white;
                border-radius: 4px;
            }
            QMenu::item {
                padding: 5px 20px 5px 20px;
            }
            QMenu::item:selected {
                background-color: #555;
            }
        """)

        add_action = menu.addAction("➕ 添加任务")
        edit_action = menu.addAction("✏️ 编辑选中")
        del_action = menu.addAction("🗑️ 删除选中")

        hide_text = "👁️ 显示已完成" if self.hide_completed else "🙈 隐藏已完成"
        hide_action = menu.addAction(hide_text)

        menu.addSeparator()
        exit_action = menu.addAction("❌ 退出程序")

        action = menu.exec_(self.mapToGlobal(event.pos()))

        if action == add_action:
            self.input_field.show()
            self.input_field.setFocus()

        elif action == edit_action:
            current_item = self.list_widget.currentItem()
            if current_item:
                widget = self.list_widget.itemWidget(current_item)
                if widget:
                    widget.start_edit()

        elif action == del_action:
            current_item = self.list_widget.currentItem()
            if current_item:
                row = self.list_widget.row(current_item)
                self.list_widget.takeItem(row)
                self.save_data()
                self.apply_visibility_logic()

        elif action == hide_action:
            self.hide_completed = not self.hide_completed
            self.apply_visibility_logic()

        elif action == exit_action:
            self.save_data()
            QApplication.quit()

    def save_data(self):
        """保存任务数据"""
        data = self.collect_tasks()

        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_data(self):
        """加载任务数据"""
        if not os.path.exists(self.data_file):
            return

        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for entry in data:
                self.create_task_item(
                    entry.get("text", ""),
                    entry.get("done", False)
                )

            self.reorder_tasks()
            self.apply_visibility_logic()

        except Exception as e:
            print("加载任务数据失败：", e)

    def mousePressEvent(self, event):
        """鼠标按下，开始拖动窗口"""
        if event.button() == Qt.LeftButton:
            self.m_drag = True
            self.m_DragPosition = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动，拖动窗口"""
        if event.buttons() == Qt.LeftButton and hasattr(self, "m_drag") and self.m_drag:
            self.move(event.globalPos() - self.m_DragPosition)
            event.accept()

    def mouseReleaseEvent(self, event):
        """鼠标松开，停止拖动窗口"""
        self.m_drag = False


if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

    app = QApplication(sys.argv)
    demo = DesktopTodo()
    demo.show()

    sys.exit(app.exec_())