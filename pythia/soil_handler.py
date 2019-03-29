def findSoilProfile(profile, soilFiles):
    profile = "*{}".format(profile)
    for sf in soilFiles:
        with open(sf) as f:
            for line in f:
                if line.startswith(profile):
                    return sf
    return None


def transpose(listOfLists):
    return list(map(list, zip(*listOfLists)))


def formatSoilData(header, current_data):
    transposed = transpose(current_data)
    return {k: v for k, v in zip(header, transposed)}


def readSoilLayers(profile, soilFile):
    profile = "*{}".format(profile)
    profilelines = []
    found = False
    with open(soilFile) as f:
        for line in f:
            line = line.strip()
            if line.startswith(profile):
                found = True
            if found and line == "":
                found = False
            if found:
                profilelines.append(line)
    in_data = False
    current_data = []
    header = []
    data = {}
    for line in profilelines:
        if line.startswith("@") and in_data:
            data.update(formatSoilData(header, current_data))
            header = []
            current_data = []
            in_data = False
        if line.startswith("@"):
            header = line[1:].split()
            if header[0] == "SLB":
                in_data = True
            else:
                in_data = False
        else:
            if in_data:
                current_data.append(line.split())
    data.update(formatSoilData(header, current_data))
    return data


def calculateSoilThickness(slb):
    thick = []
    for i, v in enumerate(slb):
        if i == 0:
            thick.append(v)
        else:
            thick.append(v - slb[i - 1])
    return thick


def calculateSoilMidpoint(slb):
    midpoint = []
    for i, v in enumerate(slb):
        if v < 40:
            midpoint.append(0.0)
        else:
            if i == 0:
                midpoint.append(0.0)
            elif slb[i - 1] > 100:
                midpoint.append(0.0)
            else:
                midpoint.append((min(100, v) + max(40, slb[i - 1])) / 2)
    return midpoint


def calculateTopFrac(slb, thickness):
    tf = []
    c = 0.0
    for i, v in enumerate(slb):
        if v < 40:
            c = 1.0
        else:
            c = 1 - ((v - 40) / thickness[i])
        tf.append(max(0.0, c))
    return tf


def calculateBotFrac(slb, thickness):
    bf = []
    c = 0.0
    for i, v in enumerate(slb):
        if i != 0:
            if slb[i - 1] > 100:
                c = 1.0
            else:
                c = (v - 100) / (thickness[i])
        bf.append(max(0.0, c))
    return bf


def calculateMidFrac(tf, bf):
    return [1 - bf[i] - tf[i] for i in range(len(tf))]


def calculateDepthFactor(mp, tf, mf):
    maths = [tf[i] + (mf[i] * (1 - (mp[i] - 40) / 60)) for i in range(len(mp))]
    return [max(0.05, m) for m in maths]


def calculateWeightingFactor(slbdm, thickness, df):
    return [slbdm[i] * thickness[i] * df[i] for i in range(len(slbdm))]


def calculateICNTOT(wf, n, twf):
    return [f * n / twf for f in wf]


def calculateNDist(icn, sbdm, thickness):
    return [icn[i] / sbdm[i] / thickness[i] for i in range(len(icn))]


def calculateH2O(fractionalAW, slll, sdul):
    h2o = []
    for i, ll in enumerate(slll):
        h2o.append((fractionalAW * (sdul[i] - ll)) + ll)
    return h2o


def calculateICLayerData(soilData, run):
    slb = [int(v) for v in soilData["SLB"]]
    sbdm = [float(v) for v in soilData["SBDM"]]
    slll = [float(v) for v in soilData["SLLL"]]
    sdul = [float(v) for v in soilData["SDUL"]]

    thickness = calculateSoilThickness(slb)
    mp = calculateSoilMidpoint(slb)
    tf = calculateTopFrac(slb, thickness)
    bf = calculateBotFrac(slb, thickness)
    mf = calculateMidFrac(tf, bf)
    df = calculateDepthFactor(mp, tf, mf)
    wf = calculateWeightingFactor(sbdm, thickness, df)

    # tsbdm = sum([thickness[i] * sbdm[i] for i in range(len(thickness))])
    twf = sum(wf)
    ictot = calculateICNTOT(wf, run["initialN"], twf)
    icndist = calculateNDist(ictot, sbdm, thickness)

    return transpose(
        [
            soilData["SLB"],
            calculateH2O(run["fractionalAW"], slll, sdul),
            [icnd * 10 * 0.1 for icnd in icndist],
            [icnd * 10 * 0.9 for icnd in icndist],
        ]
    )
