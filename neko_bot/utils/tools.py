"""Bot tools module"""


def get_readable_time(seconds: int) -> str:
    """get human readable time from seconds."""
    up_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]

    for count in range(1, 4):
        if count < 3:
            remainder, result = divmod(seconds, 60)
        else:
            remainder, result = divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for _x in range(len(time_list)):
        time_list[_x] = str(time_list[_x]) + time_suffix_list[_x]
    if len(time_list) == 4:
        up_time += time_list.pop() + ", "

    time_list.reverse()
    up_time += ":".join(time_list)

    return up_time
