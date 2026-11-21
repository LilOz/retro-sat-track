#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string_view>

namespace orbit {

inline constexpr int width = 480;
inline constexpr int height = 320;
inline constexpr std::size_t maxObjects = 5;
inline constexpr std::size_t maxOrbitPoints = 48;
inline constexpr std::size_t maxPasses = 8;
inline constexpr std::size_t maxCategories = 5;
inline constexpr std::size_t maxEntriesPerCategory = 16;

using Color = uint16_t; // RGB565

class Surface {
public:
    virtual ~Surface() = default;
    virtual void fillRect(int x, int y, int w, int h, Color color) = 0;
    virtual void line(int x1, int y1, int x2, int y2, Color color) = 0;
};

struct Position {
    // Earth-fixed Cartesian coordinates, in Earth radii.
    float x;
    float y;
    float z;
};

struct Pass {
    int64_t riseUtc;
    int durationSeconds;
    int peakDegrees;
};

struct OrbitalParameters {
    float inclinationDegrees{};
    float periodMinutes{};
    float eccentricity{};
    float raanDegrees{};
    float argumentOfPerigeeDegrees{};
};

struct Object {
    uint32_t norad{};
    std::string_view name;
    Position position{};
    float altitudeKm{};
    float speedKmPerSecond{};
    float azimuthDegrees{};
    float elevationDegrees{};
    OrbitalParameters elements{};
    std::array<Position, maxOrbitPoints> orbit{};
    std::size_t orbitCount{};
    // Sorted by rise time, with each pass represented once.
    std::array<Pass, maxPasses> passes{};
    std::size_t passCount{};
};

struct CatalogEntry {
    uint32_t norad{};
    std::string_view name;
};

struct Category {
    std::string_view name;
    std::array<CatalogEntry, maxEntriesPerCategory> entries{};
    std::size_t entryCount{};
};

struct Scene {
    std::string_view observer;
    std::string_view sourceLabel;
    // Only objects with a position and sample telemetry are in the globe scene.
    std::array<Object, maxObjects> objects{};
    std::size_t objectCount{};
    std::array<Category, maxCategories> categories{};
    std::size_t categoryCount{};
};

enum class Action { previous, next, push, back, toggleHold, toggleGrid };

class Ui {
public:
    void input(Action action, const Scene& scene, int64_t nowUtc);
    void draw(Surface& surface, const Scene& scene, int64_t nowUtc) const;

private:
    enum class View { earth, rotatingEarth, categories, satellites, details, passes };

    int64_t displayTime(int64_t nowUtc) const;
    void push(const Scene& scene);
    void turn(bool forward, const Scene& scene, int64_t now);

    View view_ = View::earth;
    uint32_t selectedNorad_ = 0;
    std::size_t category_ = 0;
    std::array<std::size_t, maxCategories> satelliteRows_{};
    std::size_t selectedPass_ = 0;
    int globeLongitude_ = 8;
    int draftLongitude_ = 8;
    bool grid_ = true;
    bool held_ = false;
    int64_t heldTime_ = 0;
};

} // namespace orbit
