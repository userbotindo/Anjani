from prometheus_client import Counter, Gauge

EventCount = Counter(
    "anjani_event_count",
    "Number of events being processed",
    labelnames=["type"],
)
SpamPredictionStat = Counter(
    "anjani_spam_prediction_stat",
    "Number of spam prediction event",
    labelnames=["status"],
)
MessageStat = Counter(
    "anjani_message_stat",
    "Number of message",
    labelnames=["type"],
)
CommandCount = Counter("anjani_command_stats", "Number of coomand", labelnames=["name"])
UnhandledError = Counter("anjani_unhandled_error", "Number of unhandled error")

EventLatencySecond = Gauge(
    "anjani_event_latency",
    "Latency of event processed",
    labelnames=["type"],
    unit="second",
)
CommandLatencySecond = Gauge(
    "anjani_command_latency",
    "Latency of command processed",
    labelnames=["name"],
    unit="second",
)
