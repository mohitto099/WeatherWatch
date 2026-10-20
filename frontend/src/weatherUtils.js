// Pure helpers that turn a stored weather record into what the UI shows.
// Open-Meteo "weather_code" values are WMO codes: 0 clear ... 95-99 thunderstorm.

// Open-Meteo times are the city's local wall-clock time, so the hour tells us day or night.
export function isNightAt(observationTime) {
  const hour = parseInt(String(observationTime).slice(11, 13), 10);
  if (Number.isNaN(hour)) return false;
  return hour < 6 || hour >= 19;
}

export function sceneKind(code) {
  if (code === 0 || code === 1) return "clear";
  if (code === 2) return "partly";
  if (code === 3) return "cloudy";
  if (code === 45 || code === 48) return "fog";
  if (code >= 51 && code <= 57) return "drizzle";
  if ((code >= 61 && code <= 67) || (code >= 80 && code <= 82)) return "rain";
  if ((code >= 71 && code <= 77) || code === 85 || code === 86) return "snow";
  if (code >= 95 && code <= 99) return "storm";
  return "cloudy";
}

export function iconFor(code, night) {
  switch (sceneKind(code)) {
    case "clear": return night ? "🌙" : "☀️";
    case "partly": return night ? "☁️" : "⛅";
    case "cloudy": return "☁️";
    case "fog": return "🌫️";
    case "drizzle": return "🌦️";
    case "rain": return "🌧️";
    case "snow": return "❄️";
    case "storm": return "⛈️";
    default: return "🌡️";
  }
}

// A short, friendly tip. Severe weather wins over comfort, and strong wind adds a note.
export function adviceFor({ weather_code: code, temperature, wind_speed: wind, observation_time }) {
  const night = isNightAt(observation_time);
  const kind = sceneKind(code);
  let text;

  if (kind === "storm") {
    text = code >= 96
      ? "Thunderstorm with hail. Stay indoors and keep vehicles under cover."
      : "Thunderstorms in the area. Stay indoors and keep away from windows.";
  } else if (code === 65 || code === 67 || code === 82) {
    text = "Heavy rain. Avoid unnecessary travel and watch for waterlogged roads.";
  } else if (kind === "rain") {
    text = "Rainy out there. Carry an umbrella and watch for slippery roads.";
  } else if (kind === "drizzle") {
    text = "Light drizzle. A small umbrella or a light jacket will do.";
  } else if (kind === "snow") {
    text = code === 75 || code === 86
      ? "Heavy snow. Stay in if you can, and drive only if you must."
      : "Snowfall today. Dress warm and drive carefully.";
  } else if (kind === "fog") {
    text = "Foggy out there. Drive slowly and use low-beam lights.";
  } else if (temperature >= 38) {
    text = "Extreme heat. Stay hydrated and avoid being outside at midday.";
  } else if (temperature <= 0) {
    text = "Freezing temperatures. Bundle up and watch for ice.";
  } else if (kind === "clear") {
    if (night) text = "Clear skies tonight. A good night for stargazing.";
    else if (temperature >= 32) text = "Hot and sunny. Stay hydrated and plan outdoor time for early morning or evening.";
    else if (temperature >= 12) text = "Sunny day. Great weather to plan a hike.";
    else text = "Bright but chilly. Layer up for a walk.";
  } else if (kind === "partly") {
    text = night ? "Partly cloudy tonight. A calm evening ahead." : "Sun and clouds. A pleasant day for a walk or a ride.";
  } else {
    text = night ? "Cloudy night. Grab a jacket if you head out." : "Overcast skies. Comfortable light for a long walk.";
  }

  if (wind >= 40) text += " Strong winds, so secure loose items.";
  return { icon: iconFor(code, night), text };
}

// fetched_at is stored in UTC without a timezone marker.
export function minutesSince(iso) {
  const utc = /Z|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + "Z";
  return Math.max(0, Math.round((Date.now() - new Date(utc).getTime()) / 60000));
}

export function timeAgo(iso) {
  const m = minutesSince(iso);
  if (m < 1) return "just now";
  if (m < 60) return `${m} min ago`;
  if (m < 1440) return `${Math.round(m / 60)} h ago`;
  return `${Math.round(m / 1440)} d ago`;
}
