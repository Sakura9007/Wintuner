"""窗口背景与可选 OpenGL 渐变渲染。"""

import struct

from PyQt6.QtCore import Qt, QElapsedTimer, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPalette, QSurfaceFormat
from PyQt6.QtWidgets import QWidget

from wintuner.core.paths import write_error_log


try:
    from PyQt6.QtOpenGLWidgets import QOpenGLWidget
    from PyQt6.QtOpenGL import (
        QOpenGLShader,
        QOpenGLShaderProgram,
        QOpenGLBuffer,
        QOpenGLVertexArrayObject,
        QOpenGLVersionProfile,
        QOpenGLVersionFunctionsFactory,
    )
    _OPENGL_UI = True
    _OPENGL_IMPORT_ERROR = ''
except Exception as _gl_exc:
    QOpenGLWidget = None
    QOpenGLShader = None
    QOpenGLShaderProgram = None
    QOpenGLBuffer = None
    QOpenGLVertexArrayObject = None
    QOpenGLVersionProfile = None
    QOpenGLVersionFunctionsFactory = None
    _OPENGL_UI = False
    _OPENGL_IMPORT_ERROR = str(_gl_exc)


def _gl_surface_format():
    fmt = QSurfaceFormat()
    fmt.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
    fmt.setVersion(2, 0)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.NoProfile)
    fmt.setDepthBufferSize(0)
    fmt.setStencilBufferSize(0)
    fmt.setSamples(0)
    fmt.setAlphaBufferSize(8)
    fmt.setSwapInterval(1)
    return fmt
if _OPENGL_UI:

    class GradientGLWidget(QOpenGLWidget):
        gpuFailed = pyqtSignal()
        _GL_FLOAT = 5126
        _GL_TRIANGLES = 4
        _GL_BLEND = 3042
        _GL_SCISSOR_TEST = 3089
        _FRAME_NS = 8333334
        _VERTICES = struct.pack('6f', -1.0, -1.0, 3.0, -1.0, -1.0, 3.0)
        _VS_DESKTOP = (
            '#version 120\n'
            'attribute vec2 a_pos;\n'
            'uniform float u_time;\n'
            'varying vec2 v_uv;\n'
            'varying vec2 v_breath;\n'
            'void main(){\n'
            '    v_uv=a_pos*0.5+0.5;\n'
            '    v_breath=vec2('
            '0.5-0.5*cos(u_time*0.7662421106),'
            '0.5-0.5*cos(u_time*0.5927533309+1.22));\n'
            '    gl_Position=vec4(a_pos,0.0,1.0);\n'
            '}\n'
        )
        _FS_DESKTOP = (
            '#version 120\n'
            'varying vec2 v_uv;\n'
            'varying vec2 v_breath;\n'
            'uniform float u_left;\n'
            'uniform float u_top;\n'
            'float field2(vec2 uv,vec2 center,vec2 scale,float inner,float outer){\n'
            '    vec2 p=(uv-center)*scale;\n'
            '    return 1.0-smoothstep(inner,outer,dot(p,p));\n'
            '}\n'
            'float ign(vec2 p){'
            'return fract(52.9829189*fract(dot(p,vec2(0.06711056,0.00583715))));'
            '}\n'
            'void main(){\n'
            '    vec2 origin=vec2(u_left,u_top);\n'
            '    vec2 uv=clamp((v_uv-origin)/max(vec2(0.001),vec2(1.0)-origin),0.0,1.0);\n'
            '    float axis=clamp(uv.x*0.54+uv.y*0.46,0.0,1.0);\n'
            '    float center=clamp(1.0-abs(axis-0.52)*1.75,0.0,1.0);\n'
            '    vec3 color=mix('
            'vec3(1.0),vec3(0.985,0.969,0.994),0.20+0.15*center);\n'
            '    float pink=field2('
            'uv,vec2(0.28,0.34),vec2(0.84,1.12),0.035,0.78);\n'
            '    float purple=field2('
            'uv,vec2(0.78,0.58),vec2(0.92,1.05),0.025,0.74);\n'
            '    color=mix('
            'color,vec3(1.0,0.72,0.86),pink*(0.145+0.085*v_breath.x));\n'
            '    color=mix('
            'color,vec3(0.76,0.68,1.0),purple*(0.135+0.085*v_breath.y));\n'
            '    color=clamp('
            'color+vec3((ign(gl_FragCoord.xy)-0.5)/255.0),0.0,1.0);\n'
            '    gl_FragColor=vec4(color,1.0);\n'
            '}\n'
        )

        def __init__(self, parent=None):
            super().__init__(parent)
            self._program = None
            self._vbo = None
            self._vao = None
            self._functions = None
            self._ready = False
            self._failed = False
            self._loop_active = False
            self._has_vao = False
            self._u_time = -1
            self._u_left = -1
            self._u_top = -1
            self._last_frame_ns = 0
            self.setFormat(_gl_surface_format())
            self.setUpdateBehavior(QOpenGLWidget.UpdateBehavior.NoPartialUpdate)
            self.setAutoFillBackground(False)
            self._clock = QElapsedTimer()
            self._clock.start()
            self._frame_timer = QTimer(self)
            self._frame_timer.setSingleShot(True)
            self._frame_timer.setTimerType(Qt.TimerType.PreciseTimer)
            self._frame_timer.timeout.connect(self._request_frame)

        def _fail(self, reason):
            if self._failed:
                return
            self._failed = True
            self._ready = False
            self._stop_loop()
            write_error_log(f'GPU 背景已安全停用: {reason}')
            QTimer.singleShot(0, self.gpuFailed.emit)

        def initializeGL(self):
            if self._failed:
                return
            try:
                ctx = self.context()
                if ctx is None or not ctx.isValid():
                    raise RuntimeError('OpenGL context unavailable')
                fmt = ctx.format()
                if (fmt.majorVersion(), fmt.minorVersion()) < (2, 0):
                    raise RuntimeError(f'OpenGL {fmt.majorVersion()}.{fmt.minorVersion()} 不支持 Shader')
                profile = QOpenGLVersionProfile()
                profile.setVersion(2, 0)
                funcs = QOpenGLVersionFunctionsFactory.get(profile, ctx)
                if funcs is None:
                    raise RuntimeError(f'无法取得 OpenGL 2.0 函数表 (实际上下文 {fmt.majorVersion()}.{fmt.minorVersion()})')
                funcs.glDisable(self._GL_BLEND)
                funcs.glDisable(self._GL_SCISSOR_TEST)
                program = QOpenGLShaderProgram()
                if not program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, self._VS_DESKTOP):
                    raise RuntimeError(program.log())
                if not program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, self._FS_DESKTOP):
                    raise RuntimeError(program.log())
                program.bindAttributeLocation('a_pos', 0)
                if not program.link():
                    raise RuntimeError(program.log())
                vao = QOpenGLVertexArrayObject()
                has_vao = vao.create()
                vbo = QOpenGLBuffer(QOpenGLBuffer.Type.VertexBuffer)
                if has_vao:
                    vao.bind()
                if not vbo.create():
                    raise RuntimeError('OpenGL VBO creation failed')
                vbo.bind()
                vbo.setUsagePattern(QOpenGLBuffer.UsagePattern.StaticDraw)
                vbo.allocate(self._VERTICES, len(self._VERTICES))
                program.bind()
                program.enableAttributeArray(0)
                program.setAttributeBuffer(0, self._GL_FLOAT, 0, 2, 0)
                vbo.release()
                if has_vao:
                    vao.release()
                self._functions = funcs
                self._program = program
                self._vbo = vbo
                self._vao = vao
                self._has_vao = has_vao
                self._u_time = program.uniformLocation('u_time')
                self._u_left = program.uniformLocation('u_left')
                self._u_top = program.uniformLocation('u_top')
                self._ready = True
                self._sync_geometry_uniforms()
                try:
                    ctx.aboutToBeDestroyed.connect(self._cleanup_gl)
                except Exception:
                    pass
                self._start_loop()
            except Exception as exc:
                self._fail(exc)

        def _sync_geometry_uniforms(self):
            if not self._ready or self._program is None:
                return
            w = max(1, self.width())
            h = max(1, self.height())
            self._program.bind()
            self._program.setUniformValue(self._u_left, min(0.95, 220.0 / w))
            self._program.setUniformValue(self._u_top, min(0.95, 50.0 / h))

        def resizeGL(self, w, h):
            self._sync_geometry_uniforms()

        def pause(self):
            self._stop_loop()

        def resume(self):
            self._start_loop()

        def paintGL(self):
            if not self._ready or self._failed:
                return
            try:
                self._functions.glDisable(self._GL_BLEND)
                self._functions.glDisable(self._GL_SCISSOR_TEST)
                self._program.bind()
                self._program.setUniformValue(self._u_time, self._clock.elapsed() % 120000 * 0.001)
                if self._has_vao:
                    self._vao.bind()
                else:
                    self._vbo.bind()
                    self._program.enableAttributeArray(0)
                    self._program.setAttributeBuffer(0, self._GL_FLOAT, 0, 2, 0)
                self._functions.glDrawArrays(self._GL_TRIANGLES, 0, 3)
                if self._loop_active and (not self._frame_timer.isActive()):
                    self._frame_timer.start(9)
            except Exception as exc:
                self._fail(exc)

        def _request_frame(self):
            if not self._ready or self._failed or (not self._loop_active) or (not self.isVisible()):
                return
            now = self._clock.nsecsElapsed()
            elapsed = now - self._last_frame_ns
            if self._last_frame_ns and elapsed < self._FRAME_NS:
                self._frame_timer.start(max(1, int((self._FRAME_NS - elapsed + 999999) // 1000000)))
                return
            self._last_frame_ns = now
            self.update()

        def _start_loop(self):
            if not self._ready or self._failed:
                return
            self._loop_active = True
            self._last_frame_ns = 0
            self._request_frame()

        def _stop_loop(self):
            self._loop_active = False
            self._frame_timer.stop()

        def showEvent(self, event):
            super().showEvent(event)
            self._start_loop()

        def hideEvent(self, event):
            self._stop_loop()
            super().hideEvent(event)

        def _cleanup_gl(self):
            self._stop_loop()
            if self._failed:
                return
            try:
                self.makeCurrent()
            except Exception:
                return
            try:
                if self._vbo and self._vbo.isCreated():
                    self._vbo.destroy()
                if self._vao and self._vao.isCreated():
                    self._vao.destroy()
            except Exception:
                pass
            try:
                self.doneCurrent()
            except Exception:
                pass
            self._program = None
            self._vbo = None
            self._vao = None
            self._functions = None
            self._ready = False
            self._has_vao = False
else:

    class GradientGLWidget(QWidget):
        gpuFailed = pyqtSignal()

        def __init__(self, parent=None):
            super().__init__(parent)
            QTimer.singleShot(0, self.gpuFailed.emit)
            write_error_log(f'Qt OpenGL 模块不可用，动态背景已安全禁用: {_OPENGL_IMPORT_ERROR}')

        def pause(self):
            pass

        def resume(self):
            pass


class BackgroundHost(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._gpu_failed = False
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(252, 247, 253))
        self.setPalette(pal)
        self.gradient = GradientGLWidget(self)
        self.gradient.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.gradient.gpuFailed.connect(self._disable_gradient)
        self.content = QWidget(self)
        self.content.setAutoFillBackground(False)
        self.content.setStyleSheet('background:transparent;')
        self.gradient.lower()
        self.content.raise_()

    def _disable_gradient(self):
        if self._gpu_failed:
            return
        self._gpu_failed = True
        if self.gradient.isVisible():
            self.gradient.hide()
        self.update()

    def paintEvent(self, event):
        if not self._gpu_failed:
            return
        p = QPainter(self)
        r = self.rect()
        w = max(1, self.width())
        h = max(1, self.height())
        g = QLinearGradient(0, 0, w, h)
        g.setColorAt(0.0, QColor(255, 250, 253))
        g.setColorAt(0.22, QColor(255, 247, 252))
        g.setColorAt(0.46, QColor(253, 234, 247))
        g.setColorAt(0.68, QColor(244, 232, 255))
        g.setColorAt(0.86, QColor(249, 244, 255))
        g.setColorAt(1.0, QColor(255, 255, 255))
        p.fillRect(r, g)
        p.end()

    def resizeEvent(self, event):
        r = self.rect()
        if self.gradient.geometry() != r:
            self.gradient.setGeometry(r)
        if self.content.geometry() != r:
            self.content.setGeometry(r)
        super().resizeEvent(event)

    def pause(self):
        self.gradient.pause()

    def resume(self):
        self.gradient.resume()
