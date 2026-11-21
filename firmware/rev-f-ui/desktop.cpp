#include "orbit_ui.hpp"
#include "sample_scene.hpp"

#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/keysym.h>

#include <cerrno>
#include <chrono>
#include <cstdio>
#include <optional>
#include <poll.h>

namespace {

using Clock = std::chrono::steady_clock;

unsigned long colorChannel(unsigned component, unsigned maxComponent, unsigned long mask) {
    if (mask == 0) return 0;
    unsigned shift = 0;
    while ((mask & 1) == 0) {
        mask >>= 1;
        ++shift;
    }
    return ((component * mask + maxComponent / 2) / maxComponent) << shift;
}

class X11Surface : public orbit::Surface {
public:
    X11Surface(Display* display, Window window, int screen)
        : display_(display), window_(window), visual_(DefaultVisual(display, screen)),
          frame_(XCreatePixmap(display, window, orbit::width, orbit::height,
                              DefaultDepth(display, screen))),
          gc_(XCreateGC(display, frame_, 0, nullptr)) {}

    ~X11Surface() override {
        XFreeGC(display_, gc_);
        XFreePixmap(display_, frame_);
    }

    void fillRect(int x, int y, int w, int h, orbit::Color color) override {
        if (w <= 0 || h <= 0) return;
        setColor(color);
        XFillRectangle(display_, frame_, gc_, x, y, w, h);
    }

    void line(int x1, int y1, int x2, int y2, orbit::Color color) override {
        setColor(color);
        XDrawLine(display_, frame_, gc_, x1, y1, x2, y2);
    }

    void present() const {
        XCopyArea(display_, frame_, window_, gc_, 0, 0, orbit::width, orbit::height, 0, 0);
        XFlush(display_);
    }

private:
    void setColor(orbit::Color color) {
        if (color == color_) return;
        color_ = color;
        const auto pixel = colorChannel(color >> 11, 31, visual_->red_mask)
                         | colorChannel((color >> 5) & 63, 63, visual_->green_mask)
                         | colorChannel(color & 31, 31, visual_->blue_mask);
        XSetForeground(display_, gc_, pixel);
    }

    Display* display_;
    Window window_;
    Visual* visual_;
    Pixmap frame_;
    GC gc_;
    std::optional<orbit::Color> color_;
};

std::optional<orbit::Action> encoderAction(XKeyEvent& key) {
    using orbit::Action;
    switch (XLookupKeysym(&key, 0)) {
    case XK_Left:
    case XK_Up: return key.type == KeyPress ? std::optional{Action::previous} : std::nullopt;
    case XK_Right:
    case XK_Down: return key.type == KeyPress ? std::optional{Action::next} : std::nullopt;
    }

    // Momentary controls fire on release, skipping X11's auto-repeat release/press pairs.
    if (key.type != KeyRelease) return std::nullopt;
    if (XPending(key.display) > 0) {
        XEvent next{};
        XPeekEvent(key.display, &next);
        if (next.type == KeyPress && next.xkey.keycode == key.keycode &&
            next.xkey.time == key.time) return std::nullopt;
    }

    switch (XLookupKeysym(&key, 0)) {
    case XK_Return:
    case XK_KP_Enter:
    case XK_space: return Action::push;
    case XK_Escape:
    case XK_BackSpace: return Action::back;
    case XK_h: return Action::toggleHold;
    case XK_g: return Action::toggleGrid;
    default: return std::nullopt;
    }
}

int preview(Display* display, Window window, int screen, Atom close) {
    X11Surface surface(display, window, screen);
    orbit::Ui ui;
    const auto scene = orbit::sampleScene();
    const auto start = Clock::now();
    using std::chrono::milliseconds;
    using std::chrono::seconds;

    int64_t drawnTime = -1;
    bool draw = true;
    bool expose = false;
    pollfd connection{ConnectionNumber(display), POLLIN, 0};

    while (true) {
        const auto elapsed = Clock::now() - start;
        const auto nowUtc = orbit::sampleStartUtc +
                            std::chrono::duration_cast<seconds>(elapsed).count();
        while (XPending(display) > 0) {
            XEvent event{};
            XNextEvent(display, &event);
            if (event.type == DestroyNotify) return 0;
            if (event.type == ClientMessage && static_cast<Atom>(event.xclient.data.l[0]) == close) {
                XDestroyWindow(display, window);
                return 0;
            }
            if (event.type == KeyPress && XLookupKeysym(&event.xkey, 0) == XK_q) {
                XDestroyWindow(display, window);
                return 0;
            }
            if (event.type == KeyPress || event.type == KeyRelease) {
                if (const auto action = encoderAction(event.xkey)) {
                    ui.input(*action, scene, nowUtc);
                    draw = true;
                }
            }
            if (event.type == Expose) expose = true;
        }

        if (draw || drawnTime != nowUtc) {
            ui.draw(surface, scene, nowUtc);
            drawnTime = nowUtc;
            draw = false;
            expose = true;
        }
        if (expose) {
            surface.present();
            expose = false;
        }

        const auto elapsedMs = std::chrono::duration_cast<milliseconds>(elapsed).count();
        const int waitMs = 1000 - static_cast<int>(elapsedMs % 1000);
        if (poll(&connection, 1, waitMs) < 0 && errno != EINTR) {
            std::perror("ORBIT X11 connection");
            return 1;
        }
    }
}

} // namespace

int main() {
    Display* display = XOpenDisplay(nullptr);
    if (!display) {
        std::fputs("ORBIT needs an X11 display. On Windows, run it in Ubuntu with WSLg.\n", stderr);
        return 1;
    }

    const int screen = DefaultScreen(display);
    if (DefaultVisual(display, screen)->c_class != TrueColor) {
        std::fputs("ORBIT needs a TrueColor X11 display.\n", stderr);
        XCloseDisplay(display);
        return 1;
    }
    const Window window = XCreateSimpleWindow(display, RootWindow(display, screen),
                                               0, 0, orbit::width, orbit::height, 0, 0, 0);
    XStoreName(display, window, "ORBIT Rev F - Sample");
    XSizeHints size{};
    size.flags = PMinSize | PMaxSize;
    size.min_width = size.max_width = orbit::width;
    size.min_height = size.max_height = orbit::height;
    XSetWMNormalHints(display, window, &size);
    Atom close = XInternAtom(display, "WM_DELETE_WINDOW", False);
    XSetWMProtocols(display, window, &close, 1);
    XSelectInput(display, window, ExposureMask | StructureNotifyMask | KeyPressMask | KeyReleaseMask);
    XMapRaised(display, window);
    const int result = preview(display, window, screen, close);
    XCloseDisplay(display);
    return result;
}
