
# time offset in seconds, Irriadiance (W/m^2)
STPsIrradiance = [
    (0, 200),
    (15, 200),
    (95, 1000),
    (130, 1000),
    (134, 200),
    (154, 200),
    (156, 600),
    (191, 600),
    (193, 200),
    (213, 200),
    (217.5, 1100),
    (253, 1100),
    (353, 200),
    (360, 200),
]

# time offset in seconds, Available Power (% of nameplate)
STPsIrradianceNorm = [
    (0, 20),
    (15, 20),
    (95, 100),
    (130, 100),
    (134, 20),
    (154, 20),
    (156, 60),
    (191, 60),
    (193, 20),
    (213, 20),
    (217.5, 110),
    (253, 110),
    (353, 20),
    (360, 20),
]

profiles = {
    'STPsIrradiance': STPsIrradiance,
    'STPsIrradianceNorm': STPsIrradianceNorm,
}

if __name__ == "__main__":

    pass
