#include "sample_scene.hpp"

#include <algorithm>
#include <cmath>

namespace orbit {
namespace {

Position samplePosition(float node, float inclination, float phase, float radius) {
    constexpr float radians = 0.01745329252f;
    node *= radians;
    inclination *= radians;
    phase *= radians;
    const float alongNode = radius * std::cos(phase);
    const float acrossNode = radius * std::sin(phase);
    return {alongNode * std::cos(node) - acrossNode * std::cos(inclination) * std::sin(node),
            alongNode * std::sin(node) + acrossNode * std::cos(inclination) * std::cos(node),
            acrossNode * std::sin(inclination)};
}

// The globe uses an Earth-fixed node. The sample RAAN shown in Details is inertial.
void makeOrbit(Object& object, float node, float phase) {
    const float radius = 1 + object.altitudeKm / 6371;
    object.position = samplePosition(node, object.elements.inclinationDegrees, phase, radius);
    object.orbitCount = object.orbit.size();
    for (std::size_t i = 0; i < object.orbitCount; ++i) {
        const float angle = 360.f * i / object.orbitCount;
        object.orbit[i] = samplePosition(node, object.elements.inclinationDegrees, angle, radius);
    }
}

constexpr int64_t utc(int hours, int minutes, int seconds) {
    return 3600 * hours + 60 * minutes + seconds;
}

CatalogEntry entryFor(const Object& object) {
    return {object.norad, object.name};
}

template <std::size_t Count>
Category category(std::string_view name, const CatalogEntry (&entries)[Count]) {
    static_assert(Count <= maxEntriesPerCategory);
    Category result{name};
    std::copy_n(entries, Count, result.entries.begin());
    result.entryCount = Count;
    return result;
}

} // namespace

Scene sampleScene() {
    Scene scene{};
    scene.observer = "LONDON";
    scene.sourceLabel = "SAMPLE";
    scene.objectCount = 4;

    auto& iss = scene.objects[0];
    iss = {25544, "ISS", {}, 421.6f, 7.66f, 91.4f, 18.6f,
           {51.6f, 92.8f, 0.00048f, 317.6f, 72.8f}, {}, 0,
           {{{utc(14, 32, 10), 378, 62}, {utc(16, 8, 42), 324, 31},
             {utc(17, 46, 5), 236, 14}, {utc(19, 23, 12), 201, 11}}}, 4};
    makeOrbit(iss, -42.4f, 116.3f);

    auto& tiangong = scene.objects[1];
    tiangong = {48274, "TIANGONG", {}, 389.2f, 7.68f, 227.1f, -8.1f,
                {41.5f, 92.4f, 0.00071f, 125.0f, 133.5f}, {}, 0,
                {{{utc(14, 47, 18), 296, 22}, {utc(16, 26, 29), 357, 49},
                  {utc(18, 3, 51), 257, 17}}}, 3};
    makeOrbit(tiangong, 125, 210);

    auto& hubble = scene.objects[2];
    hubble = {20580, "HST", {}, 510.8f, 7.61f, 148.9f, -19.4f,
              {28.5f, 94.7f, 0.00026f, 263.0f, 215.4f}, {}, 0, {}, 0};
    makeOrbit(hubble, 263, 148);

    auto& noaa = scene.objects[3];
    noaa = {33591, "NOAA 19", {}, 850.2f, 7.42f, 314.8f, -11.2f,
            {99.2f, 102.1f, 0.00135f, 143.0f, 88.2f}, {}, 0,
            {{{utc(15, 4, 16), 485, 37}, {utc(16, 49, 31), 613, 71},
              {utc(18, 33, 40), 398, 25}}}, 3};
    makeOrbit(noaa, 143, 160);

    scene.categoryCount = 4;
    scene.categories[0] = category("STATIONS", {entryFor(iss), entryFor(tiangong)});
    scene.categories[1] = category("WEATHER", {
        {41866, "GOES 16"},
        {51850, "GOES 18"},
        {60133, "GOES 19"},
        {40267, "HIMAWARI 8"},
        {41836, "HIMAWARI 9"},
        {38771, "METOP-B"},
        {43689, "METOP-C"},
        entryFor(noaa),
        {43013, "NOAA 20"},
        {54234, "NOAA 21"},
        {37849, "SUOMI NPP"},
    });
    scene.categories[2] = category("SCIENCE", {
        entryFor(hubble),
        {25867, "CHANDRA"},
        {25989, "XMM-NEWTON"},
        {38358, "NUSTAR"},
    });
    scene.categories[3] = category("NAVIGATION", {
        {28474, "GPS PRN 02"},
        {43873, "GPS PRN 04"},
        {27663, "GPS PRN 16"},
        {36585, "GPS PRN 25"},
    });

    return scene;
}

} // namespace orbit
