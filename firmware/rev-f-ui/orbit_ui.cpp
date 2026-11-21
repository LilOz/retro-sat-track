#include "orbit_ui.hpp"

#include <algorithm>
#include <array>
#include <cinttypes>
#include <cmath>
#include <cstdio>

namespace orbit {
namespace {

#include "coastlines.hpp"

constexpr Color rgb(int red, int green, int blue) {
    return static_cast<Color>(((red >> 3) << 11) | ((green >> 2) << 5) | (blue >> 3));
}

constexpr Color background = rgb(8, 23, 19);
constexpr Color ocean = rgb(12, 37, 28);
constexpr Color rules = rgb(25, 59, 44);
constexpr Color gridLine = rgb(31, 73, 54);
constexpr Color muted = rgb(121, 169, 135);
constexpr Color coast = rgb(87, 148, 106);
constexpr Color green = rgb(161, 248, 162);
constexpr Color pale = rgb(197, 250, 190);
constexpr Color highlight = rgb(222, 255, 152);
constexpr Color orbitFar = rgb(103, 143, 86);
constexpr Color rowFill = rgb(22, 59, 43);
constexpr float radians = 0.01745329252f;
constexpr int globeX = 144;
constexpr int globeY = 166;
constexpr int globeRadius = 130;
constexpr int mapLeft = 1;
constexpr int mapTop = 32;
constexpr int mapRight = 292;
constexpr int mapBottom = 298;

using Glyph = std::array<uint8_t, 5>;

// Column bitmaps, with bit 0 at the top.
constexpr Glyph digits[] = {
    {0x3e,0x51,0x49,0x45,0x3e}, {0x00,0x42,0x7f,0x40,0x00},
    {0x42,0x61,0x51,0x49,0x46}, {0x21,0x41,0x45,0x4b,0x31},
    {0x18,0x14,0x12,0x7f,0x10}, {0x27,0x45,0x45,0x45,0x39},
    {0x3c,0x4a,0x49,0x49,0x30}, {0x01,0x71,0x09,0x05,0x03},
    {0x36,0x49,0x49,0x49,0x36}, {0x06,0x49,0x49,0x29,0x1e},
};
constexpr Glyph letters[] = {
    {0x7e,0x11,0x11,0x11,0x7e}, {0x7f,0x49,0x49,0x49,0x36},
    {0x3e,0x41,0x41,0x41,0x22}, {0x7f,0x41,0x41,0x22,0x1c},
    {0x7f,0x49,0x49,0x49,0x41}, {0x7f,0x09,0x09,0x09,0x01},
    {0x3e,0x41,0x49,0x49,0x7a}, {0x7f,0x08,0x08,0x08,0x7f},
    {0x00,0x41,0x7f,0x41,0x00}, {0x20,0x40,0x41,0x3f,0x01},
    {0x7f,0x08,0x14,0x22,0x41}, {0x7f,0x40,0x40,0x40,0x40},
    {0x7f,0x02,0x0c,0x02,0x7f}, {0x7f,0x04,0x08,0x10,0x7f},
    {0x3e,0x41,0x41,0x41,0x3e}, {0x7f,0x09,0x09,0x09,0x06},
    {0x3e,0x41,0x51,0x21,0x5e}, {0x7f,0x09,0x19,0x29,0x46},
    {0x46,0x49,0x49,0x49,0x31}, {0x01,0x01,0x7f,0x01,0x01},
    {0x3f,0x40,0x40,0x40,0x3f}, {0x1f,0x20,0x40,0x20,0x1f},
    {0x7f,0x20,0x18,0x20,0x7f}, {0x63,0x14,0x08,0x14,0x63},
    {0x03,0x04,0x78,0x04,0x03}, {0x61,0x51,0x49,0x45,0x43},
};

Glyph glyph(char ch) {
    if (ch >= 'A' && ch <= 'Z') return letters[ch - 'A'];
    if (ch >= '0' && ch <= '9') return digits[ch - '0'];

    switch (ch) {
    case 'i': return {0x00,0x44,0x7d,0x40,0x00};
    case 'k': return {0x7f,0x10,0x28,0x44,0x00};
    case 'm': return {0x7c,0x04,0x38,0x04,0x78};
    case 'n': return {0x7c,0x08,0x04,0x04,0x78};
    case 's': return {0x48,0x54,0x54,0x54,0x20};
    case ' ': return {};
    case '.': return {0x00,0x60,0x60,0x00,0x00};
    case ':': return {0x00,0x36,0x36,0x00,0x00};
    case '/': return {0x20,0x10,0x08,0x04,0x02};
    case '-': return {0x08,0x08,0x08,0x08,0x08};
    case '^': return {0x02,0x05,0x02,0x00,0x00}; // Degree mark.
    default:
        if (ch >= 'a' && ch <= 'z') return letters[ch - 'a'];
        return {0x02,0x01,0x51,0x09,0x06};
    }
}

void text(Surface& out, int x, int y, std::string_view value, Color color,
          int scale = 1, int right = width) {
    for (char ch : value) {
        if (x + 5 * scale > right) break;
        const auto columns = glyph(ch);
        for (int col = 0; col < 5; ++col) {
            for (int row = 0; row < 7; ++row) {
                if (columns[col] & (1u << row)) {
                    out.fillRect(x + col * scale, y + row * scale, scale, scale, color);
                }
            }
        }
        x += 6 * scale;
    }
}

void horizontal(Surface& out, int y, Color color = rules) {
    out.fillRect(12, y, 456, 1, color);
}

template <typename... Args>
void print(Surface& out, int x, int y, Color color, int scale, const char* format, Args... args) {
    char buffer[48];
    std::snprintf(buffer, sizeof buffer, format, args...);
    text(out, x, y, buffer, color, scale);
}

struct Projected {
    float x;
    float y;
    float depth;
};

float dot(Position a, Position b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}

Position geographic(float latitude, float longitude) {
    const float lat = latitude * radians;
    const float lon = longitude * radians;
    return {std::cos(lat) * std::cos(lon), std::cos(lat) * std::sin(lon), std::sin(lat)};
}

Projected project(Position position) {
    static const Position toward = geographic(20, 8);
    static const Position east = geographic(0, 98);
    static const Position north = geographic(110, 8);
    return {globeX + globeRadius * dot(east, position),
            globeY - globeRadius * dot(north, position), dot(toward, position)};
}

void segment(Surface& out, Projected a, Projected b, Color color) {
    out.line(std::lround(a.x), std::lround(a.y), std::lround(b.x), std::lround(b.y), color);
}

Projected horizon(Projected a, Projected b) {
    const float fraction = a.depth / (a.depth - b.depth);
    return {a.x + fraction * (b.x - a.x), a.y + fraction * (b.y - a.y), 0};
}

void frontSegment(Surface& out, Projected a, Projected b, Color color) {
    if (a.depth < 0 && b.depth < 0) return;
    if (a.depth < 0) a = horizon(a, b);
    if (b.depth < 0) b = horizon(a, b);
    segment(out, a, b, color);
}

void circle(Surface& out, int x, int y, int radius, Color color, bool filled = false) {
    for (int dy = -radius; dy <= radius; ++dy) {
        const int dx = static_cast<int>(std::sqrt(radius * radius - dy * dy));
        if (filled) {
            out.fillRect(x - dx, y + dy, 2 * dx + 1, 1, color);
        } else {
            const int innerRadius = radius - 1;
            const int innerSquared = innerRadius * innerRadius - dy * dy;
            if (innerSquared < 0) {
                out.fillRect(x - dx, y + dy, 2 * dx + 1, 1, color);
            } else {
                const int inner = static_cast<int>(std::sqrt(innerSquared));
                out.fillRect(x - dx, y + dy, dx - inner, 1, color);
                out.fillRect(x + inner + 1, y + dy, dx - inner, 1, color);
            }
        }
    }
}

void graticule(Surface& out) {
    for (int lat = -60; lat <= 60; lat += 30) {
        auto last = project(geographic(lat, -180));
        for (int lon = -175; lon <= 180; lon += 5) {
            const auto point = project(geographic(lat, lon));
            frontSegment(out, last, point, gridLine);
            last = point;
        }
    }
    for (int lon = -180; lon < 180; lon += 30) {
        auto last = project(geographic(-90, lon));
        for (int lat = -85; lat <= 90; lat += 5) {
            const auto point = project(geographic(lat, lon));
            frontSegment(out, last, point, gridLine);
            last = point;
        }
    }
}

void drawCoasts(Surface& out) {
    std::size_t index = 0;
    for (auto size : coastRingSizes) {
        Projected last{};
        for (int i = 0; i < size; ++i) {
            const auto vertex = coastPoints[index++];
            const auto point = project(geographic(vertex.latitude * .01f, vertex.longitude * .01f));
            if (i > 0) frontSegment(out, last, point, coast);
            last = point;
        }
    }
}

bool clipAxis(float origin, float delta, float lo, float hi, float& first, float& last) {
    if (delta == 0) return origin >= lo && origin <= hi;
    const float enter = (lo - origin) / delta;
    const float exit = (hi - origin) / delta;
    first = std::max(first, std::min(enter, exit));
    last = std::min(last, std::max(enter, exit));
    return first <= last;
}

void orbitSegment(Surface& out, Projected a, Projected b, Color color) {
    const float dx = b.x - a.x;
    const float dy = b.y - a.y;
    float first = 0;
    float last = 1;
    if (clipAxis(a.x, dx, mapLeft, mapRight, first, last) &&
        clipAxis(a.y, dy, mapTop, mapBottom, first, last)) {
        segment(out, {a.x + first * dx, a.y + first * dy, 0},
                     {a.x + last * dx, a.y + last * dy, 0}, color);
    }
}

void drawOrbit(Surface& out, const Object& object) {
    const auto count = std::min(object.orbitCount, object.orbit.size());
    if (count < 2) return;

    auto last = project(object.orbit[count - 1]);
    for (std::size_t i = 0; i < count; ++i) {
        const auto point = project(object.orbit[i]);
        if ((last.depth < 0) == (point.depth < 0)) {
            orbitSegment(out, last, point, point.depth < 0 ? orbitFar : highlight);
        } else {
            const auto limb = horizon(last, point);
            orbitSegment(out, last, limb, last.depth < 0 ? orbitFar : highlight);
            orbitSegment(out, limb, point, point.depth < 0 ? orbitFar : highlight);
        }
        last = point;
    }
}

std::size_t objectCount(const Scene& scene) {
    return std::min(scene.objectCount, scene.objects.size());
}

std::size_t categoryCount(const Scene& scene) {
    return std::min(scene.categoryCount, scene.categories.size());
}

std::size_t entryCount(const Category& category) {
    return std::min(category.entryCount, category.entries.size());
}

std::size_t validRow(std::size_t index, std::size_t count) {
    return count == 0 ? 0 : std::min(index, count - 1);
}

std::size_t stepRow(std::size_t index, std::size_t count, bool forward) {
    const auto row = validRow(index, count);
    if (forward) return validRow(row + 1, count);
    return row == 0 ? 0 : row - 1;
}

struct Selection {
    CatalogEntry entry;
    const Object* object = nullptr;
};

Selection tracked(const Object& object) {
    return {{object.norad, object.name}, &object};
}

Selection selectedObject(const Scene& scene, uint32_t norad) {
    const auto objects = objectCount(scene);
    const auto categories = categoryCount(scene);
    if (norad != 0) {
        for (std::size_t i = 0; i < objects; ++i) {
            if (scene.objects[i].norad == norad) return tracked(scene.objects[i]);
        }
        for (std::size_t i = 0; i < categories; ++i) {
            const auto& category = scene.categories[i];
            for (std::size_t j = 0; j < entryCount(category); ++j) {
                const auto& entry = category.entries[j];
                if (entry.norad == norad) return {entry};
            }
        }
    }
    if (objects != 0) return tracked(scene.objects[0]);
    for (std::size_t i = 0; i < categories; ++i) {
        const auto& category = scene.categories[i];
        if (entryCount(category) != 0) return {category.entries[0]};
    }
    return {};
}

template <typename RowName>
void picker(Surface& out, std::size_t count, std::size_t selected, RowName name,
            std::string_view empty) {
    constexpr std::size_t visibleRows = 7;
    constexpr int top = 43;
    constexpr int pitch = 36;
    constexpr int rowHeight = 31;

    if (count == 0) {
        text(out, 18, 55, empty, pale, 2);
        return;
    }

    selected = validRow(selected, count);
    const auto maxStart = count > visibleRows ? count - visibleRows : 0;
    const auto start = selected > 3 ? std::min(selected - 3, maxStart) : 0;
    const auto end = std::min(start + visibleRows, count);
    for (std::size_t i = start; i < end; ++i) {
        const int y = top + static_cast<int>(i - start) * pitch;
        if (i == selected) out.fillRect(12, y, 438, rowHeight, rowFill);
        text(out, 20, y + 8, name(i), i == selected ? pale : green, 2, 444);
        if (i + 1 < end) out.fillRect(12, y + rowHeight + 2, 438, 1, rules);
    }

    if (maxStart != 0) {
        constexpr int trackHeight = (visibleRows - 1) * pitch + rowHeight;
        const int thumbHeight = trackHeight * visibleRows / count;
        const int thumbOffset = (trackHeight - thumbHeight) * start / maxStart;
        out.fillRect(460, top, 2, trackHeight, rules);
        out.fillRect(459, top + thumbOffset, 4, thumbHeight, muted);
    }
    print(out, 410, 309, muted, 1, "%02u / %02u", static_cast<unsigned>(selected + 1),
          static_cast<unsigned>(count));
}

bool passEnded(const Pass& pass, int64_t now) {
    return pass.riseUtc + pass.durationSeconds <= now;
}

std::size_t passEnd(const Object& object) {
    return std::min(object.passCount, object.passes.size());
}

std::size_t firstPass(const Object& object, int64_t now) {
    const auto end = passEnd(object);
    std::size_t start = 0;
    while (start < end && passEnded(object.passes[start], now)) ++start;
    return start;
}

std::size_t wrapped(std::size_t index, std::size_t count, bool forward) {
    return (index + (forward ? 1 : count - 1)) % count;
}

bool markerFits(Projected point, int margin) {
    return point.depth >= 0 && point.x >= mapLeft + margin && point.x <= mapRight - margin
           && point.y >= mapTop + margin && point.y <= mapBottom - margin;
}

void globe(Surface& out, const Scene& scene, const Object* selected, bool grid) {
    circle(out, globeX, globeY, globeRadius, ocean, true);
    if (grid) graticule(out);
    drawCoasts(out);
    circle(out, globeX, globeY, globeRadius, coast);
    if (selected) drawOrbit(out, *selected);
    for (std::size_t i = 0; i < objectCount(scene); ++i) {
        const auto& object = scene.objects[i];
        if (&object == selected) continue;
        const auto mark = project(object.position);
        if (!markerFits(mark, 2)) continue;
        out.fillRect(std::lround(mark.x) - 2, std::lround(mark.y) - 2, 5, 5, green);
    }
    if (!selected) return;
    const auto mark = project(selected->position);
    if (markerFits(mark, 8)) {
        const int x = std::lround(mark.x);
        const int y = std::lround(mark.y);
        circle(out, x, y, 8, highlight);
        out.fillRect(x - 2, y - 2, 5, 5, highlight);
    }
}

void nextPass(Surface& out, const Object& object, bool observerConfigured, int64_t now) {
    text(out, 308, 140, "NEXT PASS", muted);
    const auto first = firstPass(object, now);
    if (!observerConfigured) {
        text(out, 308, 162, "SET OBSERVER", pale, 2);
    } else if (first == passEnd(object)) {
        text(out, 308, 162, "NO PASSES", pale, 2);
    } else {
        const auto& pass = object.passes[first];
        const auto remaining = pass.riseUtc - now;
        if (remaining <= 0) {
            text(out, 308, 162, "IN PROGRESS", highlight, 2);
        } else if (remaining >= 3600) {
            print(out, 308, 162, highlight, 2, "T-%02" PRId64 ":%02" PRId64 ":%02" PRId64,
                  remaining / 3600, remaining / 60 % 60, remaining % 60);
        } else {
            print(out, 308, 162, highlight, 2, "T-%02" PRId64 ":%02" PRId64,
                  remaining / 60, remaining % 60);
        }
        print(out, 308, 198, green, 1, "PEAK %d^", pass.peakDegrees);
        print(out, 308, 221, green, 1, "DUR %02d:%02d",
              pass.durationSeconds / 60, pass.durationSeconds % 60);
    }
}

void earth(Surface& out, const Scene& scene, const Selection& selected, bool grid, int64_t now) {
    globe(out, scene, selected.object, grid);
    out.fillRect(294, 43, 1, 248, rules);
    if (selected.entry.norad == 0) {
        text(out, 308, 73, "NO OBJECTS", pale, 2);
        return;
    }

    const auto nameScale = selected.entry.name.size() <= 8 ? 3 : 2;
    text(out, 308, 55, "SELECTED", muted);
    text(out, 308, 72, selected.entry.name, green, nameScale, 468);
    print(out, 308, 103, green, 1, "NORAD %" PRIu32, selected.entry.norad);

    if (selected.object) {
        nextPass(out, *selected.object, !scene.observer.empty(), now);
    } else {
        text(out, 308, 140, "SAMPLE DATA", muted);
        text(out, 308, 162, "UNAVAILABLE", pale, 2);
    }

    if (!scene.observer.empty()) {
        text(out, 308, 259, scene.observer, muted, 1, 425);
        const int utcX = 308 + static_cast<int>(std::min(scene.observer.size(), std::size_t{19})) * 6;
        text(out, utcX, 259, " / UTC", muted);
    }
    print(out, 308, 280, muted, 1, "%02u OBJECTS", static_cast<unsigned>(objectCount(scene)));
}

void details(Surface& out, const Object& object, bool observerConfigured) {
    constexpr int left = 18;
    constexpr int right = 254;
    out.fillRect(237, 43, 1, 106, rules);
    horizontal(out, 155);

    text(out, left, 44, "TELEMETRY", green);
    text(out, right, 44, "LOOK ANGLES", green);
    text(out, left, 66, "ALTITUDE", muted);
    text(out, right, 66, "AZIMUTH", muted);
    text(out, left, 108, "SPEED", muted);
    text(out, right, 108, "ELEVATION", muted);
    print(out, left, 81, pale, 2, "%.1f km", object.altitudeKm);
    print(out, left, 123, pale, 2, "%.2f km/s", object.speedKmPerSecond);
    if (observerConfigured) {
        constexpr const char* directions[] = {"N", "NE", "E", "SE", "S", "SW", "W", "NW"};
        const auto direction = static_cast<unsigned>(std::lround(object.azimuthDegrees / 45)) % 8;
        print(out, right, 81, pale, 2, "%05.1f^ %s", object.azimuthDegrees, directions[direction]);
        print(out, right, 123, pale, 2, "%.1f^", object.elevationDegrees);
    } else {
        text(out, right, 81, "--", pale, 2);
        text(out, right, 123, "--", pale, 2);
    }

    constexpr int middleOrbit = 174;
    constexpr int rightOrbit = 330;
    const auto& elements = object.elements;
    text(out, left, 169, "ORBIT", green);
    text(out, left, 191, "INCLINATION", muted);
    text(out, middleOrbit, 191, "PERIOD", muted);
    text(out, rightOrbit, 191, "ECCENTRICITY", muted);
    print(out, left, 206, pale, 2, "%.1f^", elements.inclinationDegrees);
    print(out, middleOrbit, 206, pale, 2, "%.1f min", elements.periodMinutes);
    print(out, rightOrbit, 206, pale, 2, "%.5f", elements.eccentricity);
    text(out, left, 245, "LAN", muted);
    text(out, middleOrbit, 245, "ARG OF PERIGEE", muted);
    print(out, left, 260, pale, 2, "%.1f^", elements.raanDegrees);
    print(out, middleOrbit, 260, pale, 2, "%.1f^", elements.argumentOfPerigeeDegrees);
}

void passes(Surface& out, const Scene& scene, const Object& object, std::size_t row, int64_t now) {
    text(out, 15, 50, "RISE / UTC", muted);
    text(out, 238, 50, "PEAK", muted);
    text(out, 350, 50, "DURATION", muted);
    const auto first = firstPass(object, now);
    const auto end = passEnd(object);
    constexpr std::size_t visibleRows = 3;

    if (scene.observer.empty()) {
        text(out, 18, 88, "SET OBSERVER", pale, 2);
    } else if (first == end) {
        text(out, 18, 88, "NO UPCOMING PASSES", pale, 2);
    } else {
        row = std::min(row, end - first - 1);
        const auto start = first + (row < visibleRows ? 0 : row - visibleRows + 1);
        for (std::size_t i = start; i < std::min(start + visibleRows, end); ++i) {
            const int y = 72 + static_cast<int>(i - start) * 64;
            if (i == first + row) out.fillRect(12, y, 456, 49, rowFill);
            horizontal(out, y + 52);
            const auto& pass = object.passes[i];
            const auto daySecond = ((pass.riseUtc % 86400) + 86400) % 86400;
            print(out, 18, y + 9, green, 2, "%02" PRId64 ":%02" PRId64 ":%02" PRId64,
                  daySecond / 3600, daySecond / 60 % 60, daySecond % 60);
            print(out, 241, y + 9, green, 2, "%d^", pass.peakDegrees);
            print(out, 351, y + 9, green, 2, "%02d:%02d",
                  pass.durationSeconds / 60, pass.durationSeconds % 60);
        }
    }

    text(out, 14, 275, "GEOMETRIC / OBSERVER", muted);
    text(out, 146, 275, scene.observer.empty() ? "UNSET" : scene.observer, muted, 1, 468);
}

} // namespace

int64_t Ui::displayTime(int64_t nowUtc) const {
    return held_ ? heldTime_ : nowUtc;
}

void Ui::input(Action action, const Scene& scene, int64_t nowUtc) {
    switch (action) {
    case Action::back:
        view_ = view_ == View::satellites ? View::categories : View::earth;
        break;
    case Action::push:
        push(scene);
        break;
    case Action::previous:
    case Action::next:
        turn(action == Action::next, scene, displayTime(nowUtc));
        break;
    case Action::toggleGrid:
        grid_ = !grid_;
        break;
    case Action::toggleHold:
        held_ = !held_;
        if (held_) heldTime_ = nowUtc;
        break;
    }
}

void Ui::push(const Scene& scene) {
    const auto count = categoryCount(scene);
    category_ = validRow(category_, count);
    switch (view_) {
    case View::earth:
        if (selectedObject(scene, selectedNorad_).entry.norad != 0) view_ = View::details;
        break;
    case View::categories:
        if (count != 0) view_ = View::satellites;
        break;
    case View::satellites: {
        if (count == 0) break;
        const auto& category = scene.categories[category_];
        const auto entries = entryCount(category);
        if (entries == 0) break;
        const auto row = validRow(satelliteRows_[category_], entries);
        selectedNorad_ = category.entries[row].norad;
        view_ = View::earth;
        break;
    }
    case View::details:
        selectedPass_ = 0;
        view_ = View::passes;
        break;
    case View::passes:
        break;
    }
}

void Ui::turn(bool forward, const Scene& scene, int64_t now) {
    const auto count = categoryCount(scene);
    category_ = validRow(category_, count);
    switch (view_) {
    case View::earth:
        if (count != 0) view_ = View::categories;
        break;
    case View::categories:
        category_ = stepRow(category_, count, forward);
        break;
    case View::satellites: {
        if (count == 0) break;
        auto& row = satelliteRows_[category_];
        row = stepRow(row, entryCount(scene.categories[category_]), forward);
        break;
    }
    case View::passes: {
        const auto selected = selectedObject(scene, selectedNorad_);
        if (!selected.object) break;
        const auto& object = *selected.object;
        const auto size = passEnd(object) - firstPass(object, now);
        if (size != 0) selectedPass_ = wrapped(validRow(selectedPass_, size), size, forward);
        break;
    }
    case View::details:
        break;
    }
}

void Ui::draw(Surface& out, const Scene& scene, int64_t nowUtc) const {
    out.fillRect(0, 0, width, height, background);
    horizontal(out, 30);
    horizontal(out, 300);
    text(out, 392, 15, scene.sourceLabel, muted, 1, 468);
    if (held_) text(out, 433, 15, "HOLD", highlight);

    const auto categories = categoryCount(scene);
    const auto categoryIndex = validRow(category_, categories);
    if (view_ == View::categories) {
        text(out, 12, 10, "ORBIT / CATEGORIES", green, 2);
        picker(out, categories, categoryIndex,
               [&scene](std::size_t i) { return scene.categories[i].name; }, "NO CATEGORIES");
        return;
    }
    if (view_ == View::satellites) {
        const auto& category = scene.categories[categoryIndex];
        text(out, 12, 10, "ORBIT / ", green, 2);
        text(out, 108, 10, categories == 0 ? "SATELLITES" : category.name, green, 2, 384);
        picker(out, categories == 0 ? 0 : entryCount(category), satelliteRows_[categoryIndex],
               [&category](std::size_t i) { return category.entries[i].name; }, "NO SATELLITES");
        return;
    }

    const auto selected = selectedObject(scene, selectedNorad_);
    const auto now = displayTime(nowUtc);
    if (view_ == View::earth) {
        text(out, 12, 10, "ORBIT / EARTH", green, 2);
        earth(out, scene, selected, grid_, now);
        text(out, 12, 309, "ROTATE SELECT / PUSH DETAILS", green);
    } else if (view_ == View::details) {
        text(out, 12, 10, "ORBIT / DETAILS", green, 2);
        text(out, 204, 15, selected.entry.name, muted, 1, 384);
        if (selected.object) {
            details(out, *selected.object, !scene.observer.empty());
        } else {
            text(out, 18, 72, "SAMPLE DATA UNAVAILABLE", pale, 2);
        }
        text(out, 12, 309, "PUSH PASSES / HOLD RETURN", green);
    } else {
        text(out, 12, 10, "ORBIT / NEXT PASSES", green, 2);
        text(out, 252, 15, selected.entry.name, muted, 1, 384);
        if (selected.object) {
            passes(out, scene, *selected.object, selectedPass_, now);
        } else {
            text(out, 18, 72, "SAMPLE DATA UNAVAILABLE", pale, 2);
        }
        text(out, 12, 309, "ROTATE PASS / HOLD RETURN", green);
    }
}

} // namespace orbit
