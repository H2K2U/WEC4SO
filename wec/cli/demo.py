# cli/demo.py   (внешний скрипт запуска)

from wec import Geometry, StaticLevels, HydrologicalSeries, WECAnalyzer

def main() -> None:
    """
    geom = Geometry(
        headwater_marks=[87, 89, 91, 93, 95, 97, 99, 101, 103],
        average_volumes=[0.1, 0.4, 0.9, 2.3, 4.6, 8.8, 14.6, 21, 29.3],
        lowwater_marks=[81, 83, 85, 87, 89, 91],
        lowwater_inflows=[100, 460, 1200, 2250, 3800, 5100],
    )
    levels = StaticLevels(nrl=102, dead=97)
    series = HydrologicalSeries(
        months=list(range(1, 13)),
        domestic_inflows=[540, 450, 740, 2850, 3500, 1100, 750, 630, 450, 465, 560, 410],
        guaranteed_capacity=[140, 155, 110, 230, 230, 160, 30, 100, 60, 100, 110, 130],
    )
    """
    geom = Geometry(
        headwater_marks=[455.5, 455.75, 456, 456.5, 456.75, 457, 457.25, 457.5, 459],
        average_volumes=[15.75, 23.62, 31.5, 47.25, 55.12, 63, 71, 77, 94.5],
        lowwater_marks=[431, 431.5, 432.5, 433.5, 434, 434.5, 435.0, 436.0],
        lowwater_inflows=[1000, 1500, 3350, 6100, 7900, 9900, 12200, 16000],
    )
    levels = StaticLevels(nrl=458, dead=450)
    series = HydrologicalSeries(
        months=list(range(1, 13)),
        domestic_inflows=[540, 450, 740, 2850, 3500, 1100, 750, 630, 450, 465, 560, 410],
        guaranteed_capacity=[160, 115, 120, 180, 180, 140, 50, 64, 50, 110, 115, 100],
    )

    wec = WECAnalyzer(geom, levels, series)
    df = wec.simulate()
    print(df)
    wec.plot_domestic_inflow()
    wec.plot_guaranteed_capacity()
    wec.plot_reservoir_levels(df)

if __name__ == "__main__":
    main()
