from src.config import load_species_table, load_zone_table


def test_species_table_loads_all_seven():
    table = load_species_table()
    assert set(table.species) == {"bear", "cougar", "coyote", "deer", "elk", "moose", "raccoon"}
    assert table.species["moose"].risk_tier == "critical"
    assert table.risk_priority == ["critical", "high", "medium", "low"]


def test_risk_rank_orders_by_priority():
    table = load_species_table()
    assert table.risk_rank("critical") < table.risk_rank("high") < table.risk_rank("medium") < table.risk_rank("low")
    assert table.risk_rank("unknown-tier") == len(table.risk_priority)


def test_zone_table_loads_three_zones():
    table = load_zone_table()
    names = {z.name for z in table.zones}
    assert names == {"zone1", "zone2", "zone3"}

    zone3 = next(z for z in table.zones if z.name == "zone3")
    assert zone3.led.color_rgb == (255, 0, 0)
    assert zone3.led.pattern == "flash"
    assert zone3.buzzer.pattern == "continuous-rapid"
    assert zone3.oled.show_species is True

    zone1 = next(z for z in table.zones if z.name == "zone1")
    assert zone1.led is None
    assert zone1.buzzer is None
    assert zone1.oled is None
