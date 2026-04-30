def ip_anomaly(ip_rate, avg, z, z_limit, multiplier):
    if z > z_limit:
        return True, "z-score"

    if ip_rate > avg * multiplier:
        return True, "5x baseline"

    return False, "-"


def global_anomaly(global_rate, avg, z, z_limit, multiplier):
    if z > z_limit:
        return True, "z-score"

    if global_rate > avg * multiplier:
        return True, "5x baseline"

    return False, "-"
