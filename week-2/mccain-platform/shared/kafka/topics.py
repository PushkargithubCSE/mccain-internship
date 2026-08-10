from enum import Enum


class KafkaTopics(str, Enum):
    ORDER_CREATED = "order.created"
    INVENTORY_RESERVED = "inventory.reserved"
    PAYMENT_SUCCESS = "payment.success"
    PAYMENT_FAILED = "payment.failed"
    SHIPMENT_CREATED = "shipment.created"
    SHIPMENT_DELIVERED = "shipment.delivered"