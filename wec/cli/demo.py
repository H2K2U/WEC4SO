import argparse
from wec import Geometry, StaticLevels, HydrologicalSeries, WECAnalyzer

def run_variant(vid: int):
    # 0) исходные данные
    DOMESTIC = [540, 450, 740, 2850, 3500, 1100, 750, 630, 450, 465, 560, 410]
    INSTALLED = 500
    MONTHS = list(range(1, 13))

    # 1) геометрии
    geom_A = dict(
        headwater_marks=[87, 89, 91, 93, 95, 97, 99, 101, 103],
        average_volumes=[0.1, 0.4, 0.9, 2.3, 4.6, 8.8, 14.6, 21, 29.3],
        lowwater_marks=[81, 83, 85, 87, 89, 91],
        lowwater_inflows=[100, 460, 1200, 2250, 3800, 5100],
        nrl=102, dead=97
    )
    geom_B = dict(
        headwater_marks=[110.6, 115, 120, 125, 130, 135, 138],
        average_volumes=[0, 0.15, 0.2, 0.35, 0.83, 1.38, 2],
        lowwater_marks=[109.1, 109.5, 110, 111, 112, 113],
        lowwater_inflows=[309, 492, 721, 1500, 2660, 4000],
        nrl=138, dead=120
    )
    geom_C = dict(
        headwater_marks=[455.5, 455.75, 456, 456.5, 456.75, 457, 457.25, 457.5, 459],
        average_volumes=[15.75, 23.62, 31.5, 47.25, 55.12, 63, 71, 77, 94.5],
        lowwater_marks=[431, 431.5, 432.5, 433.5, 434, 434.5, 435.0, 436.0],
        lowwater_inflows=[1000, 1500, 3350, 6100, 7900, 9900, 12200, 16000],
        nrl=458, dead=430
    )

    geometry_by_variant = {
        **{v: geom_A for v in range(1, 8)},
        **{v: geom_B for v in range(8, 18)},
        **{v: geom_C for v in range(18, 24)},
    }

    guaranteed_by_variant = {
        1: [150,130,130,200,220,160,85,100,60,130,150,140],
        2: [150,115,110,200,200,150,50,70,70,120,140,140],
        3: [120,130,135,220,190,150,85,100,70,140,150,130],
        4: [145,120,125,190,240,120,100,95,60,130,130,150],
        5: [140,155,110,230,230,160,30,100,60,100,110,130],
        6: [150,130,135,180,180,160,60,65,70,130,155,140],
        7: [130,130,135,220,200,140,50,50,50,140,140,140],
        8: [120,110,110,190,250,120,60,70,60,135,150,140],
        9: [150,115,100,230,230,130,85,90,65,120,140,140],
        10:[130,110,110,260,250,160,70,60,65,110,130,130],
        11:[130,130,140,200,230,115,100,70,60,120,150,140],
        12:[160,115,150,180,180,140,50,50,50,130,140,140],
        13:[150,130,135,200,220,160,70,75,70,110,155,140],
        14:[150,115,110,190,200,115,80,45,50,130,130,140],
        15:[120,110,115,210,200,135,60,70,75,135,150,140],
        16:[130,125,125,190,180,100,45,60,40,125,150,140],
        17:[130,120,125,200,215,160,90,80,60,110,150,140],
        18:[150,150,115,190,240,160,70,75,70,130,140,150],
        19:[150,110,130,190,210,175,60,55,55,110,140,140],
        20:[110,120,130,220,200,115,60,70,55,125,150,145],
        21:[110,120,115,120,180,105,50,40,60,140,140,130],
        22:[115,120,130,210,170,100,90,80,70,110,110,115],
        23:[160,115,120,180,180,140,50,64,50,110,115,100],
    }

    gsrc = geometry_by_variant[vid]
    geom = Geometry(
        headwater_marks=gsrc["headwater_marks"],
        average_volumes=gsrc["average_volumes"],
        lowwater_marks=gsrc["lowwater_marks"],
        lowwater_inflows=gsrc["lowwater_inflows"],
    )
    levels = StaticLevels(nrl=gsrc["nrl"], dead=gsrc["dead"], installed_capacity=INSTALLED)
    series = HydrologicalSeries(MONTHS, DOMESTIC, guaranteed_by_variant[vid])

    wec = WECAnalyzer(geom, levels, series)
    df = wec.simulate("dynamic")
    print(f"\n=== Вариант {vid} ===")
    print(df)
    wec.plot_reservoir_levels(df)

def main():
    parser = argparse.ArgumentParser(description="Run single HPP variant")
    parser.add_argument("-v", "--variant", type=int, default=1, help="variant id (1..23)")
    args = parser.parse_args()
    run_variant(args.variant)

if __name__ == "__main__":
    main()
