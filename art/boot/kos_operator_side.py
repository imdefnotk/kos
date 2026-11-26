"""The Operator in side profile (facing right). Placeholder art drawn in code.
All shapes are in local units with the red light (eye) at (0, 0), so the
character can be placed so its light sits exactly on the K.OS dot.
"""
import skia

RED = skia.Color(0xE5, 0x32, 0x2D)


def P(points_and_curves):
    """Tiny path builder: ('M',x,y) ('L',x,y) ('C',x1,y1,x2,y2,x,y) ('Z',)."""
    p = skia.Path()
    for op in points_and_curves:
        if op[0] == "M":
            p.moveTo(op[1], op[2])
        elif op[0] == "L":
            p.lineTo(op[1], op[2])
        elif op[0] == "C":
            p.cubicTo(*op[1:])
        elif op[0] == "Z":
            p.close()
    return p


# Helmet: rounded back, sloped faceplate, eye near the front of the visor.
HELMET = P([("M", -110, -222), ("C", -20, -230, 40, -170, 52, -95), ("L", 64, -20),
            ("C", 68, 20, 62, 60, 44, 96), ("C", 30, 124, 6, 142, -30, 150),
            ("L", -92, 156), ("C", -170, 150, -232, 96, -248, 10),
            ("C", -262, -100, -210, -214, -110, -222), ("Z",)])
VISOR = P([("M", -240, -22), ("C", -130, -48, 0, -56, 62, -34), ("L", 68, 30),
           ("C", 0, 42, -130, 38, -242, 16), ("Z",)])
FACEPLATE = P([("M", 64, -20), ("C", 68, 20, 62, 60, 44, 96), ("C", 30, 124, 6, 142, -30, 150),
               ("L", -40, 60), ("C", 0, 54, 40, 48, 66, 30), ("Z",)])
SEAM = P([("M", -70, -226), ("C", -170, -150, -200, -60, -196, -50)])
VENTS = [P([("M", -232, 70 + i * 18), ("L", -196, 76 + i * 18)]) for i in range(3)]

# Tall dramatic collar rising behind the head, open at the front.
COLLAR = P([("M", -330, 230), ("C", -320, 160, -300, 20, -300, -120), ("C", -296, -170, -280, -200, -262, -212),
            ("L", -228, -150), ("C", -230, -40, -210, 80, -150, 190), ("L", 40, 200), ("L", 60, 230), ("Z",)])
COLLAR_INNER = P([("M", -262, -212), ("L", -228, -150), ("C", -230, -40, -210, 80, -150, 190),
                  ("L", -180, 200), ("C", -250, 90, -272, -40, -262, -212), ("Z",)])
NECK = P([("M", -120, 120), ("L", -10, 120), ("L", 20, 210), ("L", -140, 210), ("Z",)])
# Coat: shoulder seen from the side, chest facing right.
COAT = P([("M", -560, 1000), ("C", -520, 640, -470, 380, -360, 300), ("C", -260, 240, -80, 236, 40, 262),
          ("C", 150, 290, 210, 420, 230, 1000), ("Z",)])
LAPEL = P([("M", 40, 262), ("C", 70, 420, 60, 600, 20, 1000)])
FOLDS = [P([("M", -300, 420), ("C", -330, 600, -360, 780, -380, 1000)]),
         P([("M", -150, 360), ("C", -170, 560, -160, 780, -150, 1000)]),
         P([("M", -420, 380), ("C", -460, 560, -480, 760, -500, 1000)])]

for _p_ in [COAT, LAPEL] + FOLDS:
    _p_.offset(0, -70)
SILHOUETTE = COAT
for part in (NECK, COLLAR, HELMET):
    SILHOUETTE = skia.Op(SILHOUETTE, part, skia.PathOp.kUnion_PathOp)


def _p(color, alpha=1.0, stroke=0.0, blur=0.0, cap=False):
    p = skia.Paint(Color=color, AntiAlias=True)
    p.setAlphaf(max(0.0, min(1.0, alpha)))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        if cap:
            p.setStrokeCap(skia.Paint.kRound_Cap)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


def _rim(c, path, color, alpha, dx, dy, blur):
    if alpha <= 0:
        return
    c.saveLayer(None, None)
    c.clipPath(path, doAntiAlias=True)
    c.drawPath(path, _p(color, alpha))
    cut = _p(skia.Color(0, 0, 0), 1.0, blur=blur)
    cut.setBlendMode(skia.BlendMode.kDstOut)
    c.translate(dx, dy)
    c.drawPath(path, cut)
    c.restore()


def _grad_fill(c, path, p0, p1, c0, c1):
    sh = skia.GradientShader.MakeLinear([p0, p1], [c0, c1])
    p = skia.Paint(AntiAlias=True)
    p.setShader(sh)
    c.drawPath(path, p)


def draw_body(c, white_rim=1.0, red_rim=1.0, detail=1.0, gloss=0.5, eye_light=1.0):
    """Everything except the eye itself."""
    dark = skia.Color(0x06, 0x06, 0x08)
    # coat with a soft top-down gradient
    _grad_fill(c, COAT, (0, 240), (0, 1000), skia.Color(0x14, 0x14, 0x18), dark)
    for f in FOLDS:
        c.drawPath(f, _p(skia.Color(0x1E, 0x1E, 0x24), 0.7 * detail, 3, blur=2))
    c.drawPath(LAPEL, _p(skia.Color(0x2A, 0x2A, 0x32), 0.8 * detail, 2.5))
    # neck and collar
    c.drawPath(NECK, _p(skia.Color(0x0A, 0x0A, 0x0D)))
    _grad_fill(c, COLLAR, (-300, -200), (-150, 300), skia.Color(0x16, 0x16, 0x1B), dark)
    c.drawPath(COLLAR_INNER, _p(skia.Color(0x22, 0x10, 0x12), 0.9 * detail))
    # helmet: glossy black with a broad highlight on the crown
    _grad_fill(c, HELMET, (-200, -220), (40, 140), skia.Color(0x24, 0x24, 0x2B), skia.Color(0x07, 0x07, 0x09))
    c.save()
    c.clipPath(HELMET, doAntiAlias=True)
    hx = -220 + 200 * gloss
    c.drawOval(skia.Rect(hx - 70, -235, hx + 90, -170), _p(skia.Color(0xFF, 0xFF, 0xFF), 0.18 * detail, blur=14))
    c.drawPath(SEAM, _p(skia.Color(0x30, 0x30, 0x3A), 0.9 * detail, 2))
    for v in VENTS:
        c.drawPath(v, _p(skia.Color(0x02, 0x02, 0x03), detail, 5, cap=True))
    # faceplate a touch lighter, visor band deep black with an edge highlight
    c.drawPath(FACEPLATE, _p(skia.Color(0x10, 0x10, 0x14)))
    c.drawPath(VISOR, _p(skia.Color(0x01, 0x01, 0x02)))
    c.drawPath(VISOR, _p(skia.Color(0x4A, 0x4A, 0x56), 0.6 * detail, 1.6))
    # the light reflected along the visor glass
    c.save()
    c.clipPath(VISOR, doAntiAlias=True)
    c.drawOval(skia.Rect(-160, -14, 70, 14), _p(RED, 0.35 * eye_light, blur=12))
    c.drawOval(skia.Rect(-90, -3, 60, 3), _p(skia.Color(0xFF, 0x80, 0x76), 0.35 * eye_light, blur=2))
    c.restore()
    c.restore()
    # ear module
    c.drawCircle(-120, 70, 22, _p(skia.Color(0x18, 0x18, 0x1E), detail))
    c.drawCircle(-120, 70, 22, _p(skia.Color(0x44, 0x44, 0x50), 0.7 * detail, 1.5))
    c.drawCircle(-120, 70, 7, _p(RED, 0.6 * eye_light * detail))
    # rim lights: cool white from behind (left), red from the front glow (right)
    _rim(c, SILHOUETTE, skia.Color(0xEC, 0xEC, 0xF2), 0.85 * white_rim, 6, 2, 4)
    _rim(c, HELMET, RED, 0.7 * red_rim * eye_light, -5, 1, 4)
    _rim(c, COAT, RED, 0.35 * red_rim * eye_light, -5, 1, 4)


def draw_eye(c, x, y, r, on, glow):
    """The red light. Drawn in screen space so it can stay exactly in place."""
    if on <= 0:
        c.drawCircle(x, y, r, _p(skia.Color(0x2A, 0x0C, 0x0C)))
        return
    c.drawCircle(x, y, r * (2.2 + 0.8 * glow), _p(RED, 0.38 * on * min(glow, 2.5), blur=14 + 10 * glow))
    c.drawCircle(x, y, r, _p(RED, on))
    c.drawCircle(x - r * 0.25, y - r * 0.25, r * 0.32, _p(skia.Color(0xFF, 0xA0, 0x96), 0.6 * on, blur=2))
