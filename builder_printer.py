"""
Builder Printer Pro v7.0 - نرم‌افزار حرفه‌ای طراحی نقشه ساختمان
نسخه کامل و بدون باگ
"""

import sys
import os
import pickle
import math
import random
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# ==================== کلاس Shape ====================
class Shape:
    def __init__(self, shape_type, points, color, width, fill_color=None, 
                 opacity=1.0, rotation=0, layer=0, name="",
                 dash_pattern=None, gradient=None, shadow=False, rounded_corners=0,
                 text="", font_size=12, font_family="Arial", bold=False, italic=False):
        self.type = shape_type
        self.points = points
        self.color = color
        self.width = width
        self.fill_color = fill_color
        self.opacity = opacity
        self.rotation = rotation
        self.layer = layer
        self.name = name
        self.dash_pattern = dash_pattern
        self.gradient = gradient
        self.shadow = shadow
        self.rounded_corners = rounded_corners
        self.selected = False
        self.text = text
        self.font_size = font_size
        self.font_family = font_family
        self.bold = bold
        self.italic = italic
        self.bounds = self.calculate_bounds()
        
    def calculate_bounds(self):
        if not self.points:
            return QRectF()
        min_x = min(p.x() for p in self.points)
        max_x = max(p.x() for p in self.points)
        min_y = min(p.y() for p in self.points)
        max_y = max(p.y() for p in self.points)
        return QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
    
    def contains_point(self, point):
        if not self.bounds or not self.bounds.contains(point):
            return False
        
        if self.type in ["rectangle", "filled_rect"] and len(self.points) >= 2:
            return QRectF(self.points[0], self.points[-1]).contains(point)
        elif self.type in ["ellipse", "filled_ellipse"] and len(self.points) >= 2:
            rect = QRectF(self.points[0], self.points[-1])
            cx, cy = rect.center().x(), rect.center().y()
            rx, ry = rect.width() / 2, rect.height() / 2
            if rx <= 0 or ry <= 0:
                return False
            dx = (point.x() - cx) / rx
            dy = (point.y() - cy) / ry
            return (dx * dx + dy * dy) <= 1.0
        elif self.type == "polygon" and len(self.points) >= 3:
            return QPolygonF(self.points).containsPoint(point, Qt.FillRule.OddEvenFill)
        elif self.type == "star" and len(self.points) >= 2:
            c = self.points[0]
            dx = self.points[-1].x() - c.x()
            dy = self.points[-1].y() - c.y()
            outer = math.sqrt(dx*dx + dy*dy)
            inner = outer * 0.4
            pts = []
            for i in range(10):
                a = math.pi * 2 * i / 10 - math.pi / 2
                r = outer if i % 2 == 0 else inner
                pts.append(QPointF(c.x() + r * math.cos(a), c.y() + r * math.sin(a)))
            return QPolygonF(pts).containsPoint(point, Qt.FillRule.OddEvenFill)
        elif self.type == "text":
            return self.bounds.contains(point)
        
        return False

# ==================== کلاس Layer ====================
class Layer:
    def __init__(self, name="لایه پیش‌فرض", visible=True, locked=False, opacity=1.0):
        self.name = name
        self.visible = visible
        self.locked = locked
        self.opacity = opacity
        self.shapes = []

# ==================== کلاس Canvas ====================
class CanvasWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet("background-color: white;")
        
        # متغیرهای اصلی
        self.layers = [Layer()]
        self.current_layer = 0
        self.current_points = []
        self.drawing = False
        self.selected_shapes = []
        self.clipboard = []
        
        # تنظیمات ابزار
        self.current_tool = "pencil"
        self.current_color = QColor("#000000")
        self.brush_size = 3
        self.eraser_size = 20
        self.fill_color = QColor("#FF0000")
        self.opacity = 1.0
        self.rotation = 0
        self.shadow_enabled = False
        self.gradient_mode = None
        self.dash_pattern = None
        
        # Undo/Redo
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo = 100
        
        # تنظیمات نمایش
        self.zoom_factor = 1.0
        self.snap_enabled = True
        self.snap_size = 10
        self.pan_offset = QPointF(0, 0)
        self.last_mouse_pos = QPointF()
        self.is_panning = False
        self.measurement_units = "px"
        
        # قابلیت‌های جدید
        self.grid_enabled = False
        self.grid_size = 50
        self.ruler_enabled = False
        self.snap_to_grid = False
        self.auto_save = False
        self.auto_save_file = None
        
        # تایمر برای auto-save (درست شده)
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self.check_auto_save)
        self.auto_save_timer.start(60000)  # هر دقیقه چک کن
        
    def check_auto_save(self):
        """بررسی و انجام ذخیره خودکار"""
        if self.auto_save and self.undo_stack and self.auto_save_file:
            try:
                parent = self.parent()
                if hasattr(parent, '_save'):
                    parent._save(self.auto_save_file)
                    parent.statusBar().showMessage("💾 ذخیره خودکار انجام شد")
            except:
                pass
        
    def toggle_snap(self):
        self.snap_enabled = not self.snap_enabled
        
    def toggle_grid(self):
        self.grid_enabled = not self.grid_enabled
        self.update()
        
    def toggle_ruler(self):
        self.ruler_enabled = not self.ruler_enabled
        self.update()
        
    def toggle_snap_to_grid(self):
        self.snap_to_grid = not self.snap_to_grid
        
    def zoom_in(self):
        self.zoom_factor *= 1.2
        self.zoom_factor = min(10.0, self.zoom_factor)
        self.update()
        
    def zoom_out(self):
        self.zoom_factor *= 0.8
        self.zoom_factor = max(0.1, self.zoom_factor)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # پس‌زمینه سفید
        painter.fillRect(self.rect(), Qt.GlobalColor.white)
        
        # رسم گرید (اختیاری)
        if self.grid_enabled:
            self.draw_grid(painter)
            
        # رسم خط‌کش (اختیاری)
        if self.ruler_enabled:
            self.draw_ruler(painter)
        
        # اعمال zoom و pan
        painter.save()
        painter.translate(self.pan_offset)
        painter.scale(self.zoom_factor, self.zoom_factor)
        
        # رسم لایه‌ها
        for layer in self.layers:
            if not layer.visible:
                continue
            painter.save()
            painter.setOpacity(layer.opacity)
            for shape in layer.shapes:
                if shape.selected:
                    self.draw_selection_handles(painter, shape)
                self.draw_shape(painter, shape)
            painter.restore()
        
        # رسم شکل فعلی
        if self.drawing and self.current_points:
            self.draw_current_shape(painter)
        
        painter.restore()
        
        # نمایش اطلاعات در پایین
        if self.selected_shapes:
            painter.setPen(QPen(QColor("#FF0000"), 1))
            painter.setFont(QFont("Arial", 9))
            shape = self.selected_shapes[0]
            if shape.bounds:
                info = f"نوع: {shape.type} | ابعاد: {shape.bounds.width():.0f}x{shape.bounds.height():.0f}"
                if shape.text:
                    info += f" | متن: {shape.text[:20]}"
                painter.drawText(10, self.height() - 10, info)
                
    def draw_grid(self, painter):
        """رسم گرید"""
        painter.setPen(QPen(QColor(200, 200, 200, 100), 1, Qt.PenStyle.DotLine))
        for x in range(0, int(self.width() / self.zoom_factor), self.grid_size):
            painter.drawLine(QPointF(x, 0), QPointF(x, self.height() / self.zoom_factor))
        for y in range(0, int(self.height() / self.zoom_factor), self.grid_size):
            painter.drawLine(QPointF(0, y), QPointF(self.width() / self.zoom_factor, y))
            
    def draw_ruler(self, painter):
        """رسم خط‌کش"""
        painter.save()
        painter.setPen(QPen(QColor("#333"), 1))
        painter.setFont(QFont("Arial", 8))
        
        # خط‌کش افقی
        for x in range(0, int(self.width() / self.zoom_factor), 50):
            painter.drawLine(QPointF(x, 0), QPointF(x, 10))
            if x % 100 == 0:
                painter.drawText(QPointF(x + 2, 20), str(x))
                
        # خط‌کش عمودی
        for y in range(0, int(self.height() / self.zoom_factor), 50):
            painter.drawLine(QPointF(0, y), QPointF(10, y))
            if y % 100 == 0:
                painter.drawText(QPointF(12, y + 4), str(y))
                
        painter.restore()
                
    def draw_selection_handles(self, painter, shape):
        if not shape.bounds:
            return
        painter.setPen(QPen(QColor("#0078D4"), 2))
        painter.setBrush(QBrush(QColor("white")))
        bounds = shape.bounds
        handles = [
            bounds.topLeft(), bounds.topRight(),
            bounds.bottomLeft(), bounds.bottomRight(),
            QPointF(bounds.center().x(), bounds.top()),
            QPointF(bounds.center().x(), bounds.bottom()),
            QPointF(bounds.left(), bounds.center().y()),
            QPointF(bounds.right(), bounds.center().y())
        ]
        for h in handles:
            painter.drawRect(QRectF(h.x() - 4, h.y() - 4, 8, 8))
            
    def draw_shape(self, painter, shape):
        if not shape or not shape.points:
            return
        painter.save()
        painter.setOpacity(shape.opacity)
        
        if shape.rotation != 0 and shape.bounds:
            c = shape.bounds.center()
            painter.translate(c)
            painter.rotate(shape.rotation)
            painter.translate(-c)
        
        pen = QPen(shape.color, shape.width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        if shape.dash_pattern:
            pen.setDashPattern(shape.dash_pattern)
        painter.setPen(pen)
        
        if shape.fill_color:
            if shape.gradient == "linear":
                g = QLinearGradient(shape.points[0], shape.points[-1])
                g.setColorAt(0, shape.color)
                g.setColorAt(1, shape.fill_color)
                painter.setBrush(QBrush(g))
            else:
                painter.setBrush(QBrush(shape.fill_color))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # رسم سایه
        if shape.shadow:
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 0, 0, 40)))
            off = QPointF(4, 4)
            if shape.type in ["rectangle", "filled_rect"] and len(shape.points) >= 2:
                painter.drawRect(QRectF(shape.points[0] + off, shape.points[-1] + off))
            elif shape.type in ["ellipse", "filled_ellipse"] and len(shape.points) >= 2:
                painter.drawEllipse(QRectF(shape.points[0] + off, shape.points[-1] + off))
            painter.restore()
        
        # رسم شکل اصلی
        if shape.type == "pencil":
            path = QPainterPath()
            path.moveTo(shape.points[0])
            for p in shape.points[1:]:
                path.lineTo(p)
            painter.drawPath(path)
        elif shape.type == "eraser":
            painter.setPen(QPen(Qt.GlobalColor.white, shape.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            path = QPainterPath()
            path.moveTo(shape.points[0])
            for p in shape.points[1:]:
                path.lineTo(p)
            painter.drawPath(path)
        elif shape.type in ["line", "wall", "dimension"]:
            if len(shape.points) >= 2:
                painter.drawLine(shape.points[0], shape.points[-1])
        elif shape.type in ["rectangle", "filled_rect"]:
            if len(shape.points) >= 2:
                r = QRectF(shape.points[0], shape.points[-1])
                if shape.rounded_corners > 0:
                    painter.drawRoundedRect(r, shape.rounded_corners, shape.rounded_corners)
                else:
                    painter.drawRect(r)
                if shape.text:
                    self.draw_text_in_shape(painter, shape, r)
        elif shape.type in ["ellipse", "filled_ellipse"]:
            if len(shape.points) >= 2:
                r = QRectF(shape.points[0], shape.points[-1])
                painter.drawEllipse(r)
                if shape.text:
                    self.draw_text_in_shape(painter, shape, r)
        elif shape.type == "polygon" and len(shape.points) >= 3:
            painter.drawPolygon(QPolygonF(shape.points))
        elif shape.type == "star" and len(shape.points) >= 2:
            c = shape.points[0]
            dx = shape.points[-1].x() - c.x()
            dy = shape.points[-1].y() - c.y()
            outer = math.sqrt(dx*dx + dy*dy)
            inner = outer * 0.4
            pts = []
            for i in range(10):
                a = math.pi * 2 * i / 10 - math.pi / 2
                r = outer if i % 2 == 0 else inner
                pts.append(QPointF(c.x() + r * math.cos(a), c.y() + r * math.sin(a)))
            painter.drawPolygon(QPolygonF(pts))
        elif shape.type == "arrow" and len(shape.points) >= 2:
            p1, p2 = shape.points[0], shape.points[-1]
            painter.drawLine(p1, p2)
            a = math.atan2(p2.y() - p1.y(), p2.x() - p1.x())
            s = 12
            ap1 = QPointF(p2.x() - s * math.cos(a - 0.5), p2.y() - s * math.sin(a - 0.5))
            ap2 = QPointF(p2.x() - s * math.cos(a + 0.5), p2.y() - s * math.sin(a + 0.5))
            painter.drawPolygon(QPolygonF([p2, ap1, ap2]))
        elif shape.type == "spray":
            painter.setPen(QPen(shape.color, 1))
            for p in shape.points:
                for _ in range(15):
                    x = p.x() + random.randint(-12, 12)
                    y = p.y() + random.randint(-12, 12)
                    painter.drawPoint(QPointF(x, y))
        elif shape.type == "calligraphy" and len(shape.points) >= 2:
            pen.setWidth(shape.width * 2)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            painter.setPen(pen)
            painter.drawLine(shape.points[0], shape.points[-1])
        elif shape.type == "text":
            self.draw_text_shape(painter, shape)
        
        painter.restore()
        
    def draw_text_in_shape(self, painter, shape, rect):
        """رسم متن داخل شکل"""
        if not shape.text:
            return
        painter.save()
        painter.setPen(QPen(shape.color, 1))
        font = QFont(shape.font_family, shape.font_size)
        font.setBold(shape.bold)
        font.setItalic(shape.italic)
        painter.setFont(font)
        
        text_rect = QRectF(rect.x() + 5, rect.y() + 5, 
                          rect.width() - 10, rect.height() - 10)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, shape.text)
        
        painter.restore()
        
    def draw_text_shape(self, painter, shape):
        """رسم شکل متن"""
        if not shape.points or len(shape.points) < 1:
            return
        painter.save()
        painter.setPen(QPen(shape.color, shape.width))
        font = QFont(shape.font_family, shape.font_size)
        font.setBold(shape.bold)
        font.setItalic(shape.italic)
        painter.setFont(font)
        
        pos = shape.points[0]
        painter.drawText(pos, shape.text)
        
        painter.restore()
        
    def draw_current_shape(self, painter):
        if not self.current_points:
            return
        painter.save()
        
        pen = QPen(self.current_color, self.brush_size)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        if self.dash_pattern:
            pen.setDashPattern(self.dash_pattern)
        painter.setPen(pen)
        
        if self.fill_color:
            if self.gradient_mode == "linear":
                g = QLinearGradient(self.current_points[0], self.current_points[-1])
                g.setColorAt(0, self.current_color)
                g.setColorAt(1, self.fill_color)
                painter.setBrush(QBrush(g))
            else:
                painter.setBrush(QBrush(self.fill_color))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        
        if self.current_tool == "pencil":
            path = QPainterPath()
            path.moveTo(self.current_points[0])
            for p in self.current_points[1:]:
                path.lineTo(p)
            painter.drawPath(path)
        elif self.current_tool == "eraser":
            painter.setPen(QPen(Qt.GlobalColor.white, self.eraser_size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            path = QPainterPath()
            path.moveTo(self.current_points[0])
            for p in self.current_points[1:]:
                path.lineTo(p)
            painter.drawPath(path)
        elif self.current_tool in ["line", "dimension"]:
            if len(self.current_points) >= 2:
                painter.drawLine(self.current_points[0], self.current_points[-1])
                if self.current_tool == "dimension":
                    p1, p2 = self.current_points[0], self.current_points[-1]
                    length = math.sqrt((p2.x()-p1.x())**2 + (p2.y()-p1.y())**2)
                    painter.setPen(QPen(QColor("red"), 2))
                    painter.setFont(QFont("Arial", 10))
                    mx = (p1.x() + p2.x()) / 2
                    my = (p1.y() + p2.y()) / 2 - 15
                    painter.drawText(QPointF(mx, my), f"{int(length)}{self.measurement_units}")
        elif self.current_tool in ["rectangle", "filled_rect"]:
            if len(self.current_points) >= 2:
                painter.drawRect(QRectF(self.current_points[0], self.current_points[-1]))
        elif self.current_tool in ["ellipse", "filled_ellipse"]:
            if len(self.current_points) >= 2:
                painter.drawEllipse(QRectF(self.current_points[0], self.current_points[-1]))
        elif self.current_tool == "polygon":
            if len(self.current_points) >= 3:
                painter.drawPolygon(QPolygonF(self.current_points))
            elif len(self.current_points) >= 2:
                painter.drawLine(self.current_points[0], self.current_points[-1])
        elif self.current_tool == "star" and len(self.current_points) >= 2:
            c = self.current_points[0]
            dx = self.current_points[-1].x() - c.x()
            dy = self.current_points[-1].y() - c.y()
            outer = math.sqrt(dx*dx + dy*dy)
            inner = outer * 0.4
            pts = []
            for i in range(10):
                a = math.pi * 2 * i / 10 - math.pi / 2
                r = outer if i % 2 == 0 else inner
                pts.append(QPointF(c.x() + r * math.cos(a), c.y() + r * math.sin(a)))
            painter.drawPolygon(QPolygonF(pts))
        elif self.current_tool == "arrow" and len(self.current_points) >= 2:
            p1, p2 = self.current_points[0], self.current_points[-1]
            painter.drawLine(p1, p2)
            angle = math.atan2(p2.y() - p1.y(), p2.x() - p1.x())
            s = 12
            ap1 = QPointF(p2.x() - s * math.cos(angle - 0.5), p2.y() - s * math.sin(angle - 0.5))
            ap2 = QPointF(p2.x() - s * math.cos(angle + 0.5), p2.y() - s * math.sin(angle + 0.5))
            painter.drawPolygon(QPolygonF([p2, ap1, ap2]))
        elif self.current_tool == "wall":
            painter.setPen(QPen(QColor("black"), 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            if len(self.current_points) >= 2:
                painter.drawLine(self.current_points[0], self.current_points[-1])
        elif self.current_tool == "spray":
            painter.setPen(QPen(self.current_color, 1))
            for _ in range(40):
                x = self.current_points[-1].x() + random.randint(-18, 18)
                y = self.current_points[-1].y() + random.randint(-18, 18)
                painter.drawPoint(QPointF(x, y))
        elif self.current_tool == "calligraphy" and len(self.current_points) >= 2:
            pen.setWidth(self.brush_size * 2)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            painter.setPen(pen)
            painter.drawLine(self.current_points[0], self.current_points[-1])
        elif self.current_tool == "text":
            if len(self.current_points) >= 1:
                pos = self.current_points[0]
                painter.setFont(QFont("Arial", 14))
                painter.drawText(pos, "متن")
        
        painter.restore()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = self.screen_to_canvas(event.position())
            pos = self.snap_point(pos)
            
            # ابزار رنگ‌آمیزی
            if self.current_tool == "fill":
                self.flood_fill(pos)
                return
            
            # ابزار متن
            if self.current_tool == "text":
                text, ok = QInputDialog.getText(self, "متن", "متن مورد نظر را وارد کنید:")
                if ok and text:
                    shape = Shape("text", [pos], self.current_color, self.brush_size,
                                 None, self.opacity, 0, self.current_layer, "text",
                                 text=text, font_size=14)
                    self.layers[self.current_layer].shapes.append(shape)
                    self.undo_stack.append(("add", shape, self.current_layer))
                    self.redo_stack.clear()
                    self.update()
                return
            
            # ابزار انتخاب
            if self.current_tool == "select":
                for layer in reversed(self.layers):
                    if not layer.visible or layer.locked:
                        continue
                    for shape in reversed(layer.shapes):
                        if shape.contains_point(pos):
                            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                                shape.selected = not shape.selected
                                if shape.selected:
                                    self.selected_shapes.append(shape)
                                else:
                                    self.selected_shapes.remove(shape)
                            else:
                                self.deselect_all()
                                shape.selected = True
                                self.selected_shapes.append(shape)
                            self.update()
                            return
                self.deselect_all()
                return
            
            self.drawing = True
            self.current_points = [pos]
            self.last_mouse_pos = pos
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.is_panning = True
            self.last_mouse_pos = event.position()
    
    def flood_fill(self, pos):
        """رنگ‌آمیزی هوشمند"""
        for layer in reversed(self.layers):
            if not layer.visible or layer.locked:
                continue
            for shape in reversed(layer.shapes):
                if shape.contains_point(pos):
                    old_fill = shape.fill_color
                    shape.fill_color = QColor(self.fill_color) if self.fill_color else None
                    self.undo_stack.append(("fill", shape, old_fill, self.layers.index(layer)))
                    self.redo_stack.clear()
                    self.update()
                    try:
                        self.parent().statusBar().showMessage(f"✅ شکل با رنگ {self.fill_color.name()} پر شد")
                    except:
                        pass
                    return
        
        try:
            self.parent().statusBar().showMessage("❌ هیچ شکلی برای رنگ‌آمیزی پیدا نشد")
        except:
            pass
            
    def mouseMoveEvent(self, event):
        pos = self.screen_to_canvas(event.position())
        if self.is_panning:
            delta = event.position() - self.last_mouse_pos
            self.pan_offset += delta
            self.last_mouse_pos = event.position()
            self.update()
            return
        if self.drawing:
            pos = self.snap_point(pos)
            if self.current_tool in ["pencil", "eraser", "spray", "calligraphy"]:
                self.current_points.append(pos)
            else:
                if len(self.current_points) >= 2:
                    self.current_points[-1] = pos
                else:
                    self.current_points.append(pos)
            self.update()
        else:
            try:
                self.parent().statusBar().showMessage(
                    f"X: {pos.x():.0f}, Y: {pos.y():.0f} | Zoom: {self.zoom_factor*100:.0f}% | {self.current_tool}")
            except:
                pass
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.drawing:
            self.drawing = False
            if self.current_points:
                self.finalize_shape()
            self.current_points = []
            self.update()
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.is_panning = False
            
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_factor *= 1.15
        else:
            self.zoom_factor *= 0.85
        self.zoom_factor = max(0.1, min(10.0, self.zoom_factor))
        self.update()
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected()
        elif event.key() == Qt.Key.Key_Escape:
            self.deselect_all()
        elif event.key() == Qt.Key.Key_G and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.toggle_grid()
        elif event.key() == Qt.Key.Key_R and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.toggle_ruler()
            
    def screen_to_canvas(self, pos):
        x = (pos.x() - self.pan_offset.x()) / self.zoom_factor
        y = (pos.y() - self.pan_offset.y()) / self.zoom_factor
        return QPointF(x, y)
        
    def snap_point(self, pos):
        if not self.snap_enabled:
            return pos
        if self.snap_to_grid:
            x = round(pos.x() / self.grid_size) * self.grid_size
            y = round(pos.y() / self.grid_size) * self.grid_size
        else:
            x = round(pos.x() / self.snap_size) * self.snap_size
            y = round(pos.y() / self.snap_size) * self.snap_size
        return QPointF(x, y)
        
    def finalize_shape(self):
        if not self.current_points:
            return
        shape = Shape(
            self.current_tool,
            self.current_points.copy(),
            QColor(self.current_color),
            self.brush_size if self.current_tool != "eraser" else self.eraser_size,
            QColor(self.fill_color) if self.fill_color else None,
            self.opacity, self.rotation, self.current_layer,
            f"{self.current_tool}_{len(self.layers[self.current_layer].shapes)}",
            self.dash_pattern, self.gradient_mode, self.shadow_enabled
        )
        self.layers[self.current_layer].shapes.append(shape)
        self.undo_stack.append(("add", shape, self.current_layer))
        self.redo_stack.clear()
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)
            
    def undo(self):
        if not self.undo_stack:
            return
        action, *args = self.undo_stack.pop()
        if action == "add":
            shape, layer_idx = args
            self.layers[layer_idx].shapes.remove(shape)
            self.redo_stack.append(("remove", shape, layer_idx))
        elif action == "remove":
            shape, layer_idx = args
            self.layers[layer_idx].shapes.append(shape)
            self.redo_stack.append(("add", shape, layer_idx))
        elif action == "fill":
            shape, old_fill, layer_idx = args
            shape.fill_color = old_fill
            self.redo_stack.append(("fill", shape, shape.fill_color, layer_idx))
        self.update()
        
    def redo(self):
        if not self.redo_stack:
            return
        action, *args = self.redo_stack.pop()
        if action == "add":
            shape, layer_idx = args
            self.layers[layer_idx].shapes.append(shape)
            self.undo_stack.append(("add", shape, layer_idx))
        elif action == "remove":
            shape, layer_idx = args
            self.layers[layer_idx].shapes.remove(shape)
            self.undo_stack.append(("remove", shape, layer_idx))
        elif action == "fill":
            shape, old_fill, layer_idx = args
            shape.fill_color = old_fill
            self.undo_stack.append(("fill", shape, shape.fill_color, layer_idx))
        self.update()
        
    def delete_selected(self):
        for shape in self.selected_shapes[:]:
            for layer in self.layers:
                if shape in layer.shapes:
                    layer.shapes.remove(shape)
                    self.undo_stack.append(("remove", shape, self.layers.index(layer)))
        self.selected_shapes.clear()
        self.update()
        
    def deselect_all(self):
        for shape in self.selected_shapes:
            shape.selected = False
        self.selected_shapes.clear()
        self.update()
        
    def clear_all(self):
        for layer in self.layers:
            layer.shapes.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.selected_shapes.clear()
        self.update()

# ==================== کلاس اصلی برنامه ====================
class BuilderPrinter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Builder Printer Pro v7.0 - طراحی نقشه ساختمان")
        self.setGeometry(100, 100, 1400, 850)
        
        self.current_file = None
        self.canvas = CanvasWidget(self)
        self.setCentralWidget(self.canvas)
        
        self.setup_menu()
        self.setup_toolbars()
        self.setup_panels()
        self.setup_statusbar()
        
        # استایل حرفه‌ای
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QToolBar { background-color: #2d2d2d; border: none; padding: 4px; spacing: 4px; }
            QPushButton { background-color: #3a3a3a; color: white; border: 1px solid #555;
                         border-radius: 4px; padding: 6px 12px; font-size: 13px; }
            QPushButton:hover { background-color: #4a4a4a; }
            QPushButton:checked { background-color: #0078d4; }
            QMenuBar { background-color: #2d2d2d; color: white; }
            QMenuBar::item:selected { background-color: #0078d4; }
            QMenu { background-color: #2d2d2d; color: white; border: 1px solid #555; }
            QMenu::item:selected { background-color: #0078d4; }
            QStatusBar { background-color: #2d2d2d; color: #ccc; }
            QSpinBox, QDoubleSpinBox, QComboBox { background-color: #3a3a3a; color: white;
                                                  border: 1px solid #555; border-radius: 3px; padding: 3px; }
            QLabel { color: #ddd; }
            QGroupBox { color: #ddd; border: 1px solid #555; border-radius: 5px;
                        margin-top: 10px; padding-top: 10px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QDockWidget { color: #ddd; }
            QDockWidget::title { background-color: #2d2d2d; padding: 6px; }
        """)
        
    def setup_menu(self):
        mb = self.menuBar()
        
        # منوی فایل
        fm = mb.addMenu("فایل")
        a = QAction("📄 جدید", self); a.setShortcut("Ctrl+N"); a.triggered.connect(self.new_file); fm.addAction(a)
        a = QAction("📂 باز...", self); a.setShortcut("Ctrl+O"); a.triggered.connect(self.open_file); fm.addAction(a)
        a = QAction("💾 ذخیره", self); a.setShortcut("Ctrl+S"); a.triggered.connect(self.save_file); fm.addAction(a)
        a = QAction("💾 ذخیره با نام...", self); a.setShortcut("Ctrl+Shift+S"); a.triggered.connect(self.save_as); fm.addAction(a)
        fm.addSeparator()
        a = QAction("⚙ تنظیمات...", self); a.setShortcut("Ctrl+,"); a.triggered.connect(self.settings_dialog); fm.addAction(a)
        fm.addSeparator()
        em = fm.addMenu("📤 خروجی")
        a = QAction("PNG...", self); a.setShortcut("Ctrl+E"); a.triggered.connect(self.export_png); em.addAction(a)
        a = QAction("JPG...", self); a.triggered.connect(self.export_jpg); em.addAction(a)
        fm.addSeparator()
        a = QAction("❌ خروج", self); a.setShortcut("Ctrl+Q"); a.triggered.connect(self.close); fm.addAction(a)
        
        # منوی ویرایش
        em = mb.addMenu("ویرایش")
        a = QAction("↩ بازگشت", self); a.setShortcut("Ctrl+Z"); a.triggered.connect(self.canvas.undo); em.addAction(a)
        a = QAction("↪ بازگردانی", self); a.setShortcut("Ctrl+Y"); a.triggered.connect(self.canvas.redo); em.addAction(a)
        em.addSeparator()
        a = QAction("✂ برش", self); a.setShortcut("Ctrl+X"); a.triggered.connect(self.cut); em.addAction(a)
        a = QAction("📋 کپی", self); a.setShortcut("Ctrl+C"); a.triggered.connect(self.copy); em.addAction(a)
        a = QAction("📌 چسباندن", self); a.setShortcut("Ctrl+V"); a.triggered.connect(self.paste); em.addAction(a)
        em.addSeparator()
        a = QAction("🔲 انتخاب همه", self); a.setShortcut("Ctrl+A"); a.triggered.connect(self.select_all); em.addAction(a)
        a = QAction("🗑 حذف", self); a.setShortcut("Delete"); a.triggered.connect(self.canvas.delete_selected); em.addAction(a)
        a = QAction("🧹 پاک کردن همه", self); a.triggered.connect(self.clear_all); em.addAction(a)
        
        # منوی نمایش
        vm = mb.addMenu("نمایش")
        a = QAction("🔍 بزرگنمایی", self); a.setShortcut("Ctrl++"); a.triggered.connect(self.canvas.zoom_in); vm.addAction(a)
        a = QAction("🔍 کوچکنمایی", self); a.setShortcut("Ctrl+-"); a.triggered.connect(self.canvas.zoom_out); vm.addAction(a)
        vm.addSeparator()
        a = QAction("🎯 اسنپ", self); a.setCheckable(True); a.setChecked(True); a.triggered.connect(self.canvas.toggle_snap); vm.addAction(a)
        a = QAction("📏 گرید", self); a.setCheckable(True); a.setChecked(False); a.setShortcut("Ctrl+G"); a.triggered.connect(self.canvas.toggle_grid); vm.addAction(a)
        a = QAction("📐 خط‌کش", self); a.setCheckable(True); a.setChecked(False); a.setShortcut("Ctrl+R"); a.triggered.connect(self.canvas.toggle_ruler); vm.addAction(a)
        a = QAction("🎯 اسنپ به گرید", self); a.setCheckable(True); a.setChecked(False); a.triggered.connect(self.canvas.toggle_snap_to_grid); vm.addAction(a)
        vm.addSeparator()
        a = QAction("🖥 تمام صفحه", self); a.setShortcut("F11"); a.triggered.connect(self.toggle_fullscreen); vm.addAction(a)
        
        # منوی ابزارها
        tm = mb.addMenu("ابزارها")
        a = QAction("📐 ابعاد دقیق...", self); a.setShortcut("Ctrl+D"); a.triggered.connect(self.dimension_dialog); tm.addAction(a)
        a = QAction("📑 لایه‌ها...", self); a.setShortcut("Ctrl+L"); a.triggered.connect(self.layers_dialog); tm.addAction(a)
        a = QAction("📊 آمار پروژه...", self); a.triggered.connect(self.stats_dialog); tm.addAction(a)
        
        # منوی راهنما
        hm = mb.addMenu("راهنما")
        a = QAction("📖 راهنما", self); a.setShortcut("F1"); a.triggered.connect(self.show_help); hm.addAction(a)
        a = QAction("ℹ درباره", self); a.triggered.connect(self.show_about); hm.addAction(a)
        
    def setup_toolbars(self):
        tb = QToolBar("ابزارها")
        tb.setMovable(False)
        tb.setIconSize(QSize(28, 28))
        self.addToolBar(tb)
        
        tools = [
            ("✏️", "pencil", "قلم"), ("📏", "line", "خط"),
            ("⬜", "rectangle", "مستطیل"), ("⬛", "filled_rect", "مستطیل توپر"),
            ("⭕", "ellipse", "بیضی"), ("🔵", "filled_ellipse", "بیضی توپر"),
            ("🔺", "polygon", "چندضلعی"), ("⭐", "star", "ستاره"),
            ("➡️", "arrow", "فلش"), ("🧹", "eraser", "پاک‌کن"),
            ("💨", "spray", "اسپری"), ("🖋", "calligraphy", "خوشنویسی"),
            ("📐", "dimension", "اندازه"), ("🏠", "wall", "دیوار"),
            ("👆", "select", "انتخاب"),
            ("🪣", "fill", "رنگ‌آمیزی"),
            ("📊", "text", "متن")
        ]
        
        self.tool_btns = []
        for icon, tool, tip in tools:
            btn = QPushButton(icon)
            btn.setToolTip(tip)
            btn.setFixedSize(36, 36)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, t=tool, b=btn: self.select_tool(t, b))
            tb.addWidget(btn)
            self.tool_btns.append(btn)
        
        tb.addSeparator()
        tb.addWidget(QLabel("ضخامت:"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 50)
        self.size_spin.setValue(3)
        self.size_spin.valueChanged.connect(lambda v: setattr(self.canvas, 'brush_size', v))
        tb.addWidget(self.size_spin)
        
        tb.addSeparator()
        self.color_btn = QPushButton("🎨")
        self.color_btn.setToolTip("انتخاب رنگ خط")
        self.color_btn.setStyleSheet("background-color: #000000; min-width: 32px;")
        self.color_btn.clicked.connect(self.choose_color)
        tb.addWidget(self.color_btn)
        
        tb.addSeparator()
        self.fill_color_btn = QPushButton("🖌️")
        self.fill_color_btn.setToolTip("انتخاب رنگ پر کردن")
        self.fill_color_btn.setStyleSheet("background-color: #FF0000; min-width: 32px;")
        self.fill_color_btn.clicked.connect(self.choose_fill_color)
        tb.addWidget(self.fill_color_btn)
        
        tb.addSeparator()
        tb.addWidget(QLabel("شفافیت:"))
        self.op_slider = QSlider(Qt.Orientation.Horizontal)
        self.op_slider.setRange(0, 100)
        self.op_slider.setValue(100)
        self.op_slider.setFixedWidth(80)
        self.op_slider.valueChanged.connect(lambda v: setattr(self.canvas, 'opacity', v/100.0))
        tb.addWidget(self.op_slider)
        
        # نوار ابزار دوم
        tb2 = QToolBar("پیشرفته")
        tb2.setMovable(False)
        self.addToolBar(tb2)
        
        gc = QComboBox()
        gc.addItems(["بدون گرادیانت", "خطی", "شعاعی"])
        gc.currentTextChanged.connect(lambda t: setattr(self.canvas, 'gradient_mode', 
            {"خطی": "linear", "شعاعی": "radial"}.get(t)))
        tb2.addWidget(QLabel("گرادیانت:"))
        tb2.addWidget(gc)
        
        tb2.addSeparator()
        dc = QComboBox()
        dc.addItems(["خط ممتد", "خط چین", "خط نقطه چین", "خط نقطه‌ای"])
        dc.currentTextChanged.connect(lambda t: setattr(self.canvas, 'dash_pattern',
            {"خط چین": [5,5], "خط نقطه چین": [10,5,2,5], "خط نقطه‌ای": [2,5]}.get(t)))
        tb2.addWidget(QLabel("خط:"))
        tb2.addWidget(dc)
        
        tb2.addSeparator()
        sb = QPushButton("🌓 سایه")
        sb.setCheckable(True)
        sb.clicked.connect(lambda: setattr(self.canvas, 'shadow_enabled', sb.isChecked()))
        tb2.addWidget(sb)
        
        tb2.addSeparator()
        grid_btn = QPushButton("📏 گرید")
        grid_btn.setCheckable(True)
        grid_btn.clicked.connect(self.canvas.toggle_grid)
        tb2.addWidget(grid_btn)
        
        ruler_btn = QPushButton("📐 خط‌کش")
        ruler_btn.setCheckable(True)
        ruler_btn.clicked.connect(self.canvas.toggle_ruler)
        tb2.addWidget(ruler_btn)
        
    def setup_panels(self):
        # پنل سمت چپ - رنگ‌ها
        panel = QFrame()
        panel.setFixedWidth(220)
        panel.setStyleSheet("background-color: #2d2d2d;")
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)
        
        # رنگ‌های ساختمانی
        gb = QGroupBox("رنگ‌های ساختمانی")
        gl = QVBoxLayout(gb)
        colors = {"آبی نقشه": "#0000FF", "خاکستری بتن": "#808080", "قرمز آجر": "#B22222",
                  "سبز محوطه": "#228B22", "زرد تأسیسات": "#FFD700", "قهوه‌ای چوب": "#8B4513",
                  "نارنجی": "#FF6600", "بنفش": "#800080", "سفید": "#FFFFFF", "مشکی": "#000000"}
        for name, color in colors.items():
            row = QHBoxLayout()
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setStyleSheet(f"background-color: {color}; border: 1px solid #666; border-radius: 3px;")
            btn.clicked.connect(lambda checked, c=color: self.set_color(c))
            row.addWidget(btn)
            row.addWidget(QLabel(name))
            row.addStretch()
            gl.addLayout(row)
        layout.addWidget(gb)
        
        # تنظیمات گرید
        gb2 = QGroupBox("تنظیمات گرید")
        gl2 = QVBoxLayout(gb2)
        grid_size_layout = QHBoxLayout()
        grid_size_layout.addWidget(QLabel("سایز:"))
        grid_size_spin = QSpinBox()
        grid_size_spin.setRange(10, 200)
        grid_size_spin.setValue(50)
        grid_size_spin.valueChanged.connect(lambda v: setattr(self.canvas, 'grid_size', v))
        grid_size_layout.addWidget(grid_size_spin)
        gl2.addLayout(grid_size_layout)
        layout.addWidget(gb2)
        
        layout.addStretch()
        
        dock = QDockWidget("رنگ‌ها و تنظیمات", self)
        dock.setWidget(panel)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        
        # پنل سمت راست - اطلاعات
        info_panel = QFrame()
        info_panel.setFixedWidth(250)
        info_panel.setStyleSheet("background-color: #2d2d2d;")
        info_layout = QVBoxLayout(info_panel)
        
        # اطلاعات پروژه
        gb3 = QGroupBox("اطلاعات پروژه")
        gl3 = QVBoxLayout(gb3)
        self.info_label = QLabel("تعداد اشکال: 0\nتعداد لایه‌ها: 1\nابعاد بوم: 800x600")
        self.info_label.setStyleSheet("color: #ddd; font-size: 12px;")
        gl3.addWidget(self.info_label)
        info_layout.addWidget(gb3)
        
        info_layout.addStretch()
        
        dock2 = QDockWidget("اطلاعات", self)
        dock2.setWidget(info_panel)
        dock2.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock2)
        
    def setup_statusbar(self):
        self.statusBar().showMessage("آماده ✅")
        self.time_label = QLabel()
        self.time_label.setStyleSheet("color: #ccc; padding-right: 10px;")
        self.statusBar().addPermanentWidget(self.time_label)
        
        timer = QTimer(self)
        timer.timeout.connect(self.update_time)
        timer.start(1000)
        self.update_time()
        
    def update_time(self):
        now = QDateTime.currentDateTime()
        self.time_label.setText(now.toString("HH:mm:ss - yyyy/MM/dd"))
        
    def select_tool(self, tool, button):
        for btn in self.tool_btns:
            btn.setChecked(False)
        button.setChecked(True)
        self.canvas.current_tool = tool
        names = {"pencil": "قلم", "line": "خط", "rectangle": "مستطیل", "filled_rect": "مستطیل توپر",
                 "ellipse": "بیضی", "filled_ellipse": "بیضی توپر", "polygon": "چندضلعی",
                 "star": "ستاره", "arrow": "فلش", "eraser": "پاک‌کن", "spray": "اسپری",
                 "calligraphy": "خوشنویسی", "dimension": "اندازه", "wall": "دیوار", "select": "انتخاب",
                 "fill": "رنگ‌آمیزی", "text": "متن"}
        self.statusBar().showMessage(f"🔧 {names.get(tool, tool)}")
        
    def choose_color(self):
        color = QColorDialog.getColor(self.canvas.current_color, self)
        if color.isValid():
            self.canvas.current_color = color
            self.color_btn.setStyleSheet(f"background-color: {color.name()}; min-width: 32px;")
            
    def choose_fill_color(self):
        color = QColorDialog.getColor(self.canvas.fill_color, self)
        if color.isValid():
            self.canvas.fill_color = color
            self.fill_color_btn.setStyleSheet(f"background-color: {color.name()}; min-width: 32px;")
            
    def set_color(self, color):
        self.canvas.current_color = QColor(color)
        self.color_btn.setStyleSheet(f"background-color: {color}; min-width: 32px;")
        
    def new_file(self):
        if self.canvas.undo_stack:
            r = QMessageBox.question(self, "جدید", "تغییرات ذخیره نشده! ادامه؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if r == QMessageBox.StandardButton.No:
                return
        self.canvas.clear_all()
        self.current_file = None
        self.canvas.auto_save_file = None
        self.setWindowTitle("Builder Printer Pro v7.0 - فایل جدید")
        self.statusBar().showMessage("📄 فایل جدید")
        
    def save_file(self):
        if self.current_file:
            self._save(self.current_file)
        else:
            self.save_as()
            
    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "ذخیره", "", "Builder (*.buil);;All Files (*)")
        if path:
            self.current_file = path
            self.canvas.auto_save_file = path
            self._save(path)
            
    def _save(self, path):
        try:
            data = {"version": "7.0", "date": datetime.now().isoformat(), "layers": []}
            for layer in self.canvas.layers:
                ld = {"name": layer.name, "visible": layer.visible, "locked": layer.locked,
                      "opacity": layer.opacity, "shapes": []}
                for shape in layer.shapes:
                    sd = {"type": shape.type, "points": [(p.x(), p.y()) for p in shape.points],
                          "color": shape.color.name(), "width": shape.width,
                          "fill_color": shape.fill_color.name() if shape.fill_color else None,
                          "opacity": shape.opacity, "rotation": shape.rotation,
                          "dash_pattern": shape.dash_pattern, "gradient": shape.gradient,
                          "shadow": shape.shadow, "text": shape.text,
                          "font_size": shape.font_size, "font_family": shape.font_family,
                          "bold": shape.bold, "italic": shape.italic}
                    ld["shapes"].append(sd)
                data["layers"].append(ld)
            with open(path, 'wb') as f:
                pickle.dump(data, f)
            self.setWindowTitle(f"Builder Printer Pro v7.0 - {os.path.basename(path)}")
            self.statusBar().showMessage(f"✅ ذخیره شد: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در ذخیره:\n{str(e)}")
            
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "باز کردن", "", "Builder (*.buil);;All Files (*)")
        if not path:
            return
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
            self.canvas.clear_all()
            self.canvas.layers.clear()
            for ld in data["layers"]:
                layer = Layer(ld["name"], ld["visible"], ld["locked"], ld["opacity"])
                for sd in ld["shapes"]:
                    pts = [QPointF(x, y) for x, y in sd["points"]]
                    fc = QColor(sd["fill_color"]) if sd.get("fill_color") else None
                    shape = Shape(sd["type"], pts, QColor(sd["color"]), sd["width"], fc,
                                  sd.get("opacity", 1.0), sd.get("rotation", 0),
                                  0, "", sd.get("dash_pattern"), sd.get("gradient"), sd.get("shadow", False),
                                  sd.get("text", ""), sd.get("font_size", 12), sd.get("font_family", "Arial"),
                                  sd.get("bold", False), sd.get("italic", False))
                    layer.shapes.append(shape)
                self.canvas.layers.append(layer)
            self.current_file = path
            self.canvas.auto_save_file = path
            self.setWindowTitle(f"Builder Printer Pro v7.0 - {os.path.basename(path)}")
            self.canvas.update()
            self.update_info()
            self.statusBar().showMessage(f"✅ باز شد: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در باز کردن:\n{str(e)}")
            
    def export_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "خروجی PNG", "", "PNG (*.png)")
        if path:
            img = QImage(self.canvas.size(), QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.white)
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.canvas.render(p)
            p.end()
            img.save(path, "PNG")
            self.statusBar().showMessage("✅ PNG ذخیره شد")
            
    def export_jpg(self):
        path, _ = QFileDialog.getSaveFileName(self, "خروجی JPG", "", "JPG (*.jpg)")
        if path:
            img = QImage(self.canvas.size(), QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.white)
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.canvas.render(p)
            p.end()
            img.save(path, "JPG", 95)
            self.statusBar().showMessage("✅ JPG ذخیره شد")
            
    def cut(self):
        self.copy()
        self.canvas.delete_selected()
        
    def copy(self):
        self.canvas.clipboard.clear()
        for shape in self.canvas.selected_shapes:
            self.canvas.clipboard.append(shape)
            
    def paste(self):
        for shape in self.canvas.clipboard:
            new = Shape(shape.type, [QPointF(p.x()+20, p.y()+20) for p in shape.points],
                       QColor(shape.color), shape.width,
                       QColor(shape.fill_color) if shape.fill_color else None,
                       shape.opacity, shape.rotation, self.canvas.current_layer, shape.name+"_copy",
                       text=shape.text, font_size=shape.font_size, font_family=shape.font_family,
                       bold=shape.bold, italic=shape.italic)
            self.canvas.layers[self.canvas.current_layer].shapes.append(new)
            self.canvas.undo_stack.append(("add", new, self.canvas.current_layer))
        self.canvas.update()
        
    def select_all(self):
        self.canvas.deselect_all()
        for layer in self.canvas.layers:
            if layer.visible and not layer.locked:
                for shape in layer.shapes:
                    shape.selected = True
                    self.canvas.selected_shapes.append(shape)
        self.canvas.update()
        
    def clear_all(self):
        r = QMessageBox.question(self, "پاک کردن", "همه چیز پاک شود؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self.canvas.clear_all()
            self.statusBar().showMessage("🧹 همه پاک شد")
            
    def toggle_fullscreen(self):
        self.showFullScreen() if not self.isFullScreen() else self.showNormal()
        
    def update_info(self):
        total_shapes = sum(len(layer.shapes) for layer in self.canvas.layers)
        self.info_label.setText(
            f"تعداد اشکال: {total_shapes}\n"
            f"تعداد لایه‌ها: {len(self.canvas.layers)}\n"
            f"ابعاد بوم: {self.canvas.width()}x{self.canvas.height()}\n"
            f"زوم: {self.canvas.zoom_factor*100:.0f}%\n"
            f"ابزار فعلی: {self.canvas.current_tool}"
        )
        
    def settings_dialog(self):
        d = QDialog(self)
        d.setWindowTitle("تنظیمات")
        d.setModal(True)
        layout = QFormLayout(d)
        
        snap_spin = QSpinBox()
        snap_spin.setRange(5, 50)
        snap_spin.setValue(self.canvas.snap_size)
        snap_spin.valueChanged.connect(lambda v: setattr(self.canvas, 'snap_size', v))
        layout.addRow("اندازه اسنپ:", snap_spin)
        
        grid_spin = QSpinBox()
        grid_spin.setRange(10, 200)
        grid_spin.setValue(self.canvas.grid_size)
        grid_spin.valueChanged.connect(lambda v: setattr(self.canvas, 'grid_size', v))
        layout.addRow("اندازه گرید:", grid_spin)
        
        auto_save_check = QCheckBox("فعال کردن ذخیره خودکار")
        auto_save_check.setChecked(self.canvas.auto_save)
        auto_save_check.toggled.connect(lambda v: setattr(self.canvas, 'auto_save', v))
        layout.addRow(auto_save_check)
        
        unit_combo = QComboBox()
        unit_combo.addItems(["px", "mm", "cm", "m", "inch"])
        unit_combo.setCurrentText(self.canvas.measurement_units)
        unit_combo.currentTextChanged.connect(lambda v: setattr(self.canvas, 'measurement_units', v))
        layout.addRow("واحد:", unit_combo)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(d.accept)
        buttons.rejected.connect(d.reject)
        layout.addRow(buttons)
        
        d.exec()
        
    def dimension_dialog(self):
        d = QDialog(self)
        d.setWindowTitle("ابعاد دقیق")
        d.setModal(True)
        l = QFormLayout(d)
        w = QDoubleSpinBox(); w.setRange(0.1, 1000); w.setValue(10); w.setSuffix(" متر")
        h = QDoubleSpinBox(); h.setRange(0.1, 1000); h.setValue(10); h.setSuffix(" متر")
        r = QDoubleSpinBox(); r.setRange(0, 360); r.setSuffix(" درجه")
        l.addRow("طول:", w); l.addRow("عرض:", h); l.addRow("چرخش:", r)
        b = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        b.accepted.connect(d.accept); b.rejected.connect(d.reject)
        l.addRow(b)
        if d.exec() == QDialog.DialogCode.Accepted:
            wv, hv = w.value()*50, h.value()*50
            x, y = self.canvas.width()//2, self.canvas.height()//2
            shape = Shape("rectangle", [QPointF(x-wv/2, y-hv/2), QPointF(x+wv/2, y+hv/2)],
                         self.canvas.current_color, self.canvas.brush_size, self.canvas.fill_color,
                         self.canvas.opacity, r.value(), self.canvas.current_layer, "dimension")
            self.canvas.layers[self.canvas.current_layer].shapes.append(shape)
            self.canvas.undo_stack.append(("add", shape, self.canvas.current_layer))
            self.canvas.update()
            self.statusBar().showMessage(f"✅ مستطیل {w.value()}x{h.value()} متر")
            
    def layers_dialog(self):
        d = QDialog(self)
        d.setWindowTitle("مدیریت لایه‌ها")
        d.setModal(True)
        l = QVBoxLayout(d)
        lw = QListWidget()
        for layer in self.canvas.layers:
            lw.addItem(f"{layer.name} {'👁' if layer.visible else '🚫'} {'🔒' if layer.locked else '🔓'}")
        l.addWidget(lw)
        bl = QHBoxLayout()
        for text, func in [("➕", lambda: lw.addItem(f"لایه {len(self.canvas.layers)+1} 👁 🔓")),
                          ("➖", lambda: lw.takeItem(lw.currentRow()) if lw.currentRow()>=0 else None),
                          ("⬆", lambda: self._move_layer(lw, -1)),
                          ("⬇", lambda: self._move_layer(lw, 1)),
                          ("👁", lambda: self._toggle_layer_visibility(lw)),
                          ("🔒", lambda: self._toggle_layer_lock(lw))]:
            b = QPushButton(text); b.clicked.connect(func); bl.addWidget(b)
        l.addLayout(bl)
        b = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        b.rejected.connect(d.reject); l.addWidget(b)
        d.exec()
        
    def _move_layer(self, lw, direction):
        row = lw.currentRow()
        if row < 0:
            return
        new_row = row + direction
        if 0 <= new_row < lw.count():
            item = lw.takeItem(row)
            lw.insertItem(new_row, item)
            lw.setCurrentRow(new_row)
            self.canvas.layers[row], self.canvas.layers[new_row] = self.canvas.layers[new_row], self.canvas.layers[row]
            self.canvas.update()
            
    def _toggle_layer_visibility(self, lw):
        row = lw.currentRow()
        if row >= 0 and row < len(self.canvas.layers):
            layer = self.canvas.layers[row]
            layer.visible = not layer.visible
            text = lw.item(row).text()
            if "👁" in text:
                text = text.replace("👁", "🚫")
            else:
                text = text.replace("🚫", "👁")
            lw.item(row).setText(text)
            self.canvas.update()
            
    def _toggle_layer_lock(self, lw):
        row = lw.currentRow()
        if row >= 0 and row < len(self.canvas.layers):
            layer = self.canvas.layers[row]
            layer.locked = not layer.locked
            text = lw.item(row).text()
            if "🔒" in text:
                text = text.replace("🔒", "🔓")
            else:
                text = text.replace("🔓", "🔒")
            lw.item(row).setText(text)
            
    def stats_dialog(self):
        total_shapes = sum(len(layer.shapes) for layer in self.canvas.layers)
        shape_types = {}
        for layer in self.canvas.layers:
            for shape in layer.shapes:
                shape_types[shape.type] = shape_types.get(shape.type, 0) + 1
        
        stats_text = f"**آمار پروژه**\n\n"
        stats_text += f"تعداد کل اشکال: {total_shapes}\n"
        stats_text += f"تعداد لایه‌ها: {len(self.canvas.layers)}\n\n"
        stats_text += "**تفکیک بر اساس نوع:**\n"
        for stype, count in shape_types.items():
            stats_text += f"- {stype}: {count}\n"
        
        QMessageBox.information(self, "آمار", stats_text)
        
    def show_help(self):
        QMessageBox.information(self, "راهنما", """
🏗️ **Builder Printer Pro v7.0 - راهنمای کامل**

**ابزارها:**
✏️ قلم | 📏 خط | ⬜ مستطیل | ⬛ مستطیل توپر
⭕ بیضی | 🔵 بیضی توپر | 🔺 چندضلعی | ⭐ ستاره
➡️ فلش | 🧹 پاک‌کن | 💨 اسپری | 🖋 خوشنویسی
📐 اندازه | 🏠 دیوار | 👆 انتخاب | 🪣 رنگ‌آمیزی | 📊 متن

**نحوه استفاده از رنگ‌آمیزی:**
1. شکل بکش
2. ابزار 🪣 رو انتخاب کن
3. رنگ رو از پنل انتخاب کن
4. روی شکل کلیک کن

**نحوه اضافه کردن متن:**
1. ابزار 📊 رو انتخاب کن
2. متن مورد نظر رو وارد کن
3. روی بوم کلیک کن

**میانبرها:**
Ctrl+N جدید | Ctrl+O باز | Ctrl+S ذخیره
Ctrl+Z بازگشت | Ctrl+Y بازگردانی
Ctrl+C کپی | Ctrl+V چسباندن | Ctrl+X برش
Ctrl+A انتخاب همه | Delete حذف
Ctrl+G گرید | Ctrl+R خط‌کش
Ctrl+E خروجی PNG | F11 تمام صفحه
Shift+کلیک انتخاب چندتایی
        """)
        
    def show_about(self):
        QMessageBox.about(self, "درباره", 
            "🏗️ **Builder Printer Pro v7.0**\n\n"
            "نرم‌افزار حرفه‌ای طراحی نقشه ساختمان\n"
            "توسعه‌دهنده: شرکت پارت\n"
            "نسخه: 7.0\n"
            "تاریخ: 1404"
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = BuilderPrinter()
    window.show()
    sys.exit(app.exec())
