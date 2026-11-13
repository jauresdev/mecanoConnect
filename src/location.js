const COORDINATE_PAIR =
  /(?:^|[@=,/])\s*(-?(?:\d+(?:\.\d+)?|\.\d+))\s*,\s*(-?(?:\d+(?:\.\d+)?|\.\d+))(?=$|[,&/?#;\s])/;
const GOOGLE_COORDINATES = /!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)/i;

export function parseMapLocation(value) {
  const input = value.trim();
  if (!input) return null;

  let decodedInput = input;
  try {
    decodedInput = decodeURIComponent(input);
  } catch {
    // Keep the original value if it contains an incomplete percent escape.
  }

  const match =
    decodedInput.match(GOOGLE_COORDINATES) ??
    decodedInput.match(COORDINATE_PAIR);
  if (!match) return null;

  const parsedLatitude = Number(match[1]);
  const parsedLongitude = Number(match[2]);
  if (
    !Number.isFinite(parsedLatitude) ||
    !Number.isFinite(parsedLongitude) ||
    parsedLatitude < -90 ||
    parsedLatitude > 90 ||
    parsedLongitude < -180 ||
    parsedLongitude > 180
  ) {
    return null;
  }

  return {
    latitude: Number(parsedLatitude.toFixed(6)),
    longitude: Number(parsedLongitude.toFixed(6)),
  };
}

export function calculateDistanceKm(origin, destination) {
  const toRadians = (degrees) => (degrees * Math.PI) / 180;
  const latitudeDifference = toRadians(
    destination.latitude - origin.latitude
  );
  const longitudeDifference = toRadians(
    destination.longitude - origin.longitude
  );
  const originLatitude = toRadians(origin.latitude);
  const destinationLatitude = toRadians(destination.latitude);
  const haversine =
    Math.sin(latitudeDifference / 2) ** 2 +
    Math.cos(originLatitude) *
      Math.cos(destinationLatitude) *
      Math.sin(longitudeDifference / 2) ** 2;

  return 6371 * 2 * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine));
}

export function distanceBand(distanceKm) {
  if (distanceKm <= 5) return "near";
  if (distanceKm <= 15) return "medium";
  return "far";
}
