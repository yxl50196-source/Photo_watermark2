import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QPushButton, QLabel, QVBoxLayout, QWidget, QInputDialog, QColorDialog, QListWidget, QListWidgetItem, QSlider
from PyQt5.QtGui import QPixmap, QImage, QIcon
from PyQt5.QtCore import Qt, QSize
from PIL import Image, ImageDraw, ImageFont
import os


class WatermarkApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图片水印工具")
        self.setGeometry(100, 100, 900, 700)

        # ---------------- 状态变量 ----------------
        self.images = []  # 导入图片路径列表
        self.current_image_index = 0
        self.watermarked_image = None  # 当前水印后的图片
        self.watermark_text = None
        self.watermark_image_path = None
        self.watermark_position = "右下"  # 默认九宫格位置
        self.watermark_angle = 0  # 水印旋转角度
        self.watermark_xy = None  # 手动拖拽水印坐标
        self.original_image = None  # 保存原始图像
        self.template_file = "watermark_templates.json"  # 模板文件路径
        self.templates = []  # 存储水印模板
        

        # 尝试加载模板
        self.load_templates()

        # ---------------- 主布局 ----------------
        self.layout = QVBoxLayout()

        # 图片预览
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.image_label)

        # 导入按钮
        self.import_button = QPushButton("导入图片", self)
        self.import_button.clicked.connect(self.import_image)
        self.layout.addWidget(self.import_button)

        # 添加文本水印按钮
        self.text_watermark_button = QPushButton("添加文本水印", self)
        self.text_watermark_button.clicked.connect(self.add_text_watermark)
        self.layout.addWidget(self.text_watermark_button)

        # 添加图片水印按钮
        self.image_watermark_button = QPushButton("添加图片水印", self)
        self.image_watermark_button.clicked.connect(self.add_image_watermark)
        self.layout.addWidget(self.image_watermark_button)

        # 九宫格位置按钮
        self.grid_button = QPushButton("选择九宫格位置", self)
        self.grid_button.clicked.connect(self.choose_watermark_position)
        self.layout.addWidget(self.grid_button)

        # 旋转滑块
        self.rotation_slider = QSlider(Qt.Horizontal, self)
        self.rotation_slider.setRange(0, 360)
        self.rotation_slider.setValue(0)
        self.rotation_slider.valueChanged.connect(self.rotate_watermark)
        self.layout.addWidget(self.rotation_slider)

        # 导出按钮
        self.export_button = QPushButton("导出图片", self)
        self.export_button.clicked.connect(self.export_image)
        self.layout.addWidget(self.export_button)

        # 图片列表
        self.image_list = QListWidget(self)
        self.image_list.setViewMode(QListWidget.IconMode)
        self.image_list.setIconSize(QSize(100, 100))
        self.image_list.setFixedHeight(120)
        self.image_list.clicked.connect(self.on_image_click)
        self.layout.addWidget(self.image_list)

        # 水印模板管理按钮
        self.template_button = QPushButton("水印模板", self)
        self.template_button.clicked.connect(self.manage_templates)
        self.layout.addWidget(self.template_button)

        # ---------------- 主窗口设置 ----------------
        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        # 支持拖拽导入
        self.setAcceptDrops(True)

        # 拖拽水印状态
        self.dragging = False
        self.drag_offset = (0, 0)
        self.image_label.mousePressEvent = self.watermark_mouse_press
        self.image_label.mouseMoveEvent = self.watermark_mouse_move
        self.image_label.mouseReleaseEvent = self.watermark_mouse_release

        # 设置鼠标跟踪以便捕获移动事件
        #self.image_label.setMouseTracking(True)
        #self.image_label.mousePressEvent = self.watermark_mouse_press
        #self.image_label.mouseMoveEvent = self.watermark_mouse_move
        #self.image_label.mouseReleaseEvent = self.watermark_mouse_release

    # ---------------- 拖拽导入 ----------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        file_paths = [url.toLocalFile() for url in event.mimeData().urls()]
        valid_files = [f for f in file_paths if os.path.isfile(f)]
        if valid_files:
            self.images.extend(valid_files)
            self.update_image_list()
            self.display_image(self.images[self.current_image_index])

    # ---------------- 导入图片 ----------------
    def import_image(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "选择图片", "", "Images (*.png *.jpg *.bmp *.tiff)")
        if file_paths:
            self.images.extend(file_paths)
            self.update_image_list()
            self.display_image(self.images[self.current_image_index])

    def update_image_list(self):
        self.image_list.clear()
        for path in self.images:
            pixmap = QPixmap(path).scaled(100, 100, Qt.KeepAspectRatio)
            item = QListWidgetItem(QIcon(pixmap), os.path.basename(path))
            self.image_list.addItem(item)

    def on_image_click(self):
        self.current_image_index = self.image_list.currentRow()
        self.display_image(self.images[self.current_image_index])

    # ---------------- 显示图片 ----------------
    def display_image(self, path):
        pixmap = QPixmap(path).scaled(500, 400, Qt.KeepAspectRatio)
        self.image_label.setPixmap(pixmap)
        self.original_image = Image.open(path).convert("RGBA")  # 保存原始图像
        self.watermarked_image = self.original_image.copy()  # 初始化带水印图像
        self.apply_current_watermark()

    # ---------------- 添加文本水印 ----------------
    def add_text_watermark(self):
        if not self.images:
            return
        text, ok = QInputDialog.getText(self, "文本水印", "输入水印内容：")
        if ok and text:
            font_size, ok = QInputDialog.getInt(self, "字体大小", "字体大小:", 40, 10, 200)
            if ok:
                color = QColorDialog.getColor().name()
                self.watermark_text = (text, font_size, color)
                self.apply_current_watermark()

    # ---------------- 添加图片水印 ----------------
    def add_image_watermark(self):
        if not self.images:
            return
        path, _ = QFileDialog.getOpenFileName(self, "选择水印图片", "", "Images (*.png *.jpg *.bmp *.tiff)")
        if path:
            self.watermark_image_path = path
            self.apply_current_watermark()

    # ---------------- 九宫格位置选择 ----------------
    def choose_watermark_position(self):
        positions = ["左上", "上中", "右上", "左中", "中心", "右中", "左下", "下中", "右下"]
        pos, ok = QInputDialog.getItem(self, "选择水印位置", "位置：", positions, editable=False)
        if ok:
            self.watermark_position = pos
            self.apply_current_watermark()

    # ---------------- 旋转 ----------------
    def rotate_watermark(self):
        self.watermark_angle = self.rotation_slider.value()
        self.apply_current_watermark()

    # ---------------- 应用水印 ----------------
    def apply_current_watermark(self):
        if self.watermarked_image is None:
            return

        # 从原始图像重新生成水印
        img = self.original_image.copy()

        # 默认位置
        x, y = self.get_position(img.width, img.height)
        if self.watermark_xy:
            x, y = self.watermark_xy

        # 创建画布并绘制水印
        draw = ImageDraw.Draw(img)

        # 添加文字水印
        if self.watermark_text:
            text, font_size, color = self.watermark_text
            try:
                font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                font = ImageFont.truetype(font_path, font_size)
            except:
                font = ImageFont.load_default()
            draw.text((x, y), text, font=font, fill=color)

        # 添加图片水印
        if self.watermark_image_path:
            watermark = Image.open(self.watermark_image_path).convert("RGBA")
            scale = 0.2
            w_w, w_h = watermark.size
            watermark = watermark.resize((int(img.width * scale), int(img.width * scale * w_h / w_w)))
            img.paste(watermark, (x, y), watermark)

        # 旋转
        if self.watermark_angle != 0:
            img = img.rotate(self.watermark_angle, expand=True)

        # 更新显示图像
        self.show_image(img)

        # 更新 self.watermarked_image
        self.watermarked_image = img

    # ---------------- 显示在 QLabel ----------------
    def show_image(self, img):
        img = img.convert("RGBA")
        data = img.tobytes("raw", "RGBA")
        qimg = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimg)
        self.image_label.setPixmap(pixmap.scaled(500, 400, Qt.KeepAspectRatio))

    # ---------------- 九宫格坐标 ----------------
    def get_position(self, width, height):
        obj_w, obj_h = 100, 50  # 假设水印宽高
        mapping = {
            "左上": (0, 0),
            "上中": ((width - obj_w)//2, 0),
            "右上": (width - obj_w, 0),
            "左中": (0, (height - obj_h)//2),
            "中心": ((width - obj_w)//2, (height - obj_h)//2),
            "右中": (width - obj_w, (height - obj_h)//2),
            "左下": (0, height - obj_h),
            "下中": ((width - obj_w)//2, height - obj_h),
            "右下": (width - obj_w, height - obj_h)
        }
        return mapping.get(self.watermark_position, (width-obj_w, height-obj_h))

    # ---------------- 水印模板管理 ----------------
    def manage_templates(self):
        """管理水印模板，包括保存、加载和删除模板"""
        options = ["保存当前模板", "加载模板", "删除模板"]
        choice, ok = QInputDialog.getItem(self, "管理水印模板", "选择操作:", options, editable=False)
        if ok:
            if choice == "保存当前模板":
                self.save_template()
            elif choice == "加载模板":
                self.load_template()
            elif choice == "删除模板":
                self.delete_template()

    def save_template(self):
        """保存当前水印设置为模板"""
        # 获取当前水印设置
        template = {
            "watermark_text": self.watermark_text,
            "watermark_position": self.watermark_position,
            "watermark_angle": self.watermark_angle,
            "watermark_image_path": self.watermark_image_path,
            "watermark_xy": self.watermark_xy
        }

        # 提示用户输入模板名称
        template_name, ok = QInputDialog.getText(self, "保存模板", "输入模板名称:")
        if ok and template_name:
            template["name"] = template_name
            self.templates.append(template)
            self.save_templates()

    def load_template(self):
        """加载模板"""
        template_names = [template["name"] for template in self.templates]
        template_name, ok = QInputDialog.getItem(self, "加载模板", "选择模板:", template_names, editable=False)
        if ok and template_name:
            template = next(t for t in self.templates if t["name"] == template_name)
            self.apply_template(template)

    def delete_template(self):
        """删除模板"""
        template_names = [template["name"] for template in self.templates]
        template_name, ok = QInputDialog.getItem(self, "删除模板", "选择模板:", template_names, editable=False)
        if ok and template_name:
            self.templates = [t for t in self.templates if t["name"] != template_name]
            self.save_templates()

    def apply_template(self, template):
        """应用模板到当前水印设置"""
        self.watermark_text = template["watermark_text"]
        self.watermark_position = template["watermark_position"]
        self.watermark_angle = template["watermark_angle"]
        self.watermark_image_path = template["watermark_image_path"]
        self.watermark_xy = template["watermark_xy"]
        self.apply_current_watermark()

    def save_templates(self):
        """保存模板到文件"""
        try:
            with open(self.template_file, 'w', encoding='utf-8') as f:
                json.dump(self.templates, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存模板时发生错误: {e}")

    def load_templates(self):
        """加载模板文件"""
        try:
            if os.path.exists(self.template_file):
                with open(self.template_file, 'r', encoding='utf-8') as f:
                    self.templates = json.load(f)
        except Exception as e:
            print(f"加载模板时发生错误: {e}")
    def export_image(self):
        """导出图片，保存到指定路径"""
        if not self.watermarked_image:
            print("没有添加水印的图片可导出")
            return
        try:
            # 选择保存文件夹
            save_folder = QFileDialog.getExistingDirectory(self, "选择保存文件夹")
            if not save_folder:
                print("未选择保存文件夹！")
                return
    
            # 获取文件名
            base_name = os.path.basename(self.images[self.current_image_index])
            name, ext = os.path.splitext(base_name)

            # 提示用户输入前缀
            prefix, ok = QInputDialog.getText(self, "自定义前缀", "输入前缀（可选）:")
            if not ok: prefix = ""
    
            # 提示用户输入后缀
            suffix, ok = QInputDialog.getText(self, "自定义后缀", "输入后缀（可选）:")
            if not ok: suffix = ""

            # 合并前缀和后缀
            new_name = f"{prefix}{name}{suffix}{ext}"

            # 生成完整路径
            save_path = os.path.join(save_folder, new_name)

            # 如果是 JPEG 格式，需要将图像转换为 RGB（去除透明通道）
            if ext.lower() == ".jpg" or ext.lower() == ".jpeg":
                img_to_save = self.watermarked_image.convert("RGB")  # 转换为 RGB 格式
            elif ext.lower() == ".png":
                img_to_save = self.watermarked_image  # PNG 格式保持透明通道
            else:
                img_to_save = self.watermarked_image  # 其他格式也不需要转换

            # 保存图像
            img_to_save.save(save_path)
            print(f"图片已保存到: {save_path}")
    
        except Exception as e:
            print(f"导出图片时发生错误: {e}")


    # ---------------- 拖拽水印 ----------------
    def watermark_mouse_press(self, event):
        self.dragging = True
        # 存储鼠标点击时的偏移量
        self.drag_offset = (event.pos().x() - self.watermark_xy[0] if self.watermark_xy else 0, 
                        event.pos().y() - self.watermark_xy[1] if self.watermark_xy else 0)

    def watermark_mouse_move(self, event):
        if self.dragging:
            # 根据鼠标当前位置更新水印位置
            x = event.pos().x() - self.drag_offset[0]
            y = event.pos().y() - self.drag_offset[1]

            # 更新水印位置
            self.watermark_xy = (x, y)

            # 清除原始图像的水印，然后重新应用水印
            self.apply_current_watermark()

    def watermark_mouse_release(self, event):
        self.dragging = False


if __name__ == "__main__":
    app = QApplication([])
    window = WatermarkApp()
    window.show()
    app.exec_()
