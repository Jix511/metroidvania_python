"""Small spatial helpers shared by update and rendering code."""


def near_view(rect, center, width, height, margin=0):
    half_w = width / 2 + margin
    half_h = height / 2 + margin
    return (rect.right >= center[0] - half_w and rect.left <= center[0] + half_w
            and rect.bottom >= center[1] - half_h and rect.top <= center[1] + half_h)
