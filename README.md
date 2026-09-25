# Sunset Boulevard for Home Assistant

Find the nearest [Sunset Boulevard](https://sunset-boulevard.dk/) restaurant for anyone in your household. Home Assistant shows its address and how far away it is, puts it on the map, and can tell you when someone arrives there. It also puts every restaurant on the map.

Available in English and Danish.

## Install

Requires Home Assistant 2026.3 or newer.

### With HACS

Select this button to open the integration in HACS, then select **Download**:

[![Open this repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mm98&repository=ha-sunset-boulevard&category=integration)

Or add it yourself:

1. Open **HACS**, select the three dots at the top right and pick **Custom repositories**.
2. Enter `https://github.com/mm98/ha-sunset-boulevard`, choose the type **Integration** and select **Add**.
3. Search HACS for **Sunset Boulevard**, open it and select **Download**.
4. Restart Home Assistant.

### Without HACS

1. Copy the `custom_components/sunset_boulevard` folder from this repository into the `custom_components` folder of your Home Assistant configuration.
2. Restart Home Assistant.

## Set up

Go to **Settings > Devices & services**, select **Add integration** and pick **Sunset Boulevard**. Or select this button:

[![Add the Sunset Boulevard integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=sunset_boulevard)

Then pick the person or device tracker to follow. To follow more people, add the integration again for each of them.

## What you get

### For each person you follow

| Name | Shows |
|---|---|
| Closest restaurant | The address of the nearest restaurant, for example `Vejlevej 247, 6000 Kolding`. Open it to also see the restaurant's name, a link to its page and the distance. |
| Distance to closest restaurant | How far away the nearest restaurant is, in km. |
| Closest restaurant location | A marker on the map at the nearest restaurant. |

There is also a small zone around the nearest restaurant, which moves when another restaurant becomes the nearest. Use it in automations to react when someone arrives. It is named after the person you follow: for `person.anna` it is `zone.sunset_boulevard_closest_anna`.

The zone is not listed under **Settings > Areas, labels & zones**, and a person's location does not change to it. Use it in an automation instead, like the example below.

### All restaurants on the map

Every restaurant also shows on the Home Assistant map with its own marker, named after the restaurant, for example `Kolding Storcenter`. There is nothing to set up for this, and when you follow more than one person, each restaurant still shows only once. Its value is the distance from your home in km. Open it to see the address and a link to the restaurant's page.

The **Map** in the sidebar shows them by itself. To put them on a dashboard, add a **Map** card, open its code editor and paste this. It shows the fries icon for each restaurant:

```yaml
type: map
geo_location_sources:
  - source: sunset_boulevard
    label_mode: icon
```

When a restaurant opens or closes, the map changes with it. If you rename or hide a restaurant, that stays when Home Assistant restarts.

## Example: a notification when you arrive

Create a new automation, open the three dots at the top right, pick **Edit in YAML** and paste this. Change `anna` to the person you follow.

```yaml
triggers:
  - trigger: zone
    entity_id: person.anna
    zone: zone.sunset_boulevard_closest_anna
    event: enter
actions:
  - action: notify.notify
    data:
      message: Enjoy your meal at Sunset Boulevard!
```

## Good to know

- The list of restaurants is updated once a day. If the Sunset Boulevard website cannot be reached, the last known list is used.
- Device trackers without GPS, such as your router, only work while the person is home. Away from home, the values show as unknown.

## Problems and ideas

Tell us on [GitHub](https://github.com/mm98/ha-sunset-boulevard/issues).

## Credits

The restaurant locations come from [sunset-boulevard.dk](https://sunset-boulevard.dk/restauranter/). Missing postal codes come from the official Danish list of postal codes at [Dataforsyningen](https://dataforsyningen.dk/). This integration is not made by Sunset Boulevard or connected to it.

## License

MIT, see [LICENSE](LICENSE).
