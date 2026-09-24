from order_service.application.ports.message_broker import MessageBroker
from order_service.application.ports.uow import UnitOfWork


class PublishOutboxEvents:
    """Публикация событий из Outbox в Kafka."""

    def __init__(
        self,
        uow: UnitOfWork,
        message_broker: MessageBroker,
        order_events_topic: str,
    ) -> None:
        self._uow = uow
        self._message_broker = message_broker
        self._order_events_topic = order_events_topic

    async def execute(self) -> None:
        """Опубликовать неопубликованные события."""
        async with self._uow() as uow:
            events = await uow.outbox.get_unpublished()

            for event in events:
                await self._message_broker.publish(
                    self._order_events_topic,
                    event.payload,
                )
                await uow.outbox.mark_as_published(event.id)

            await uow.commit()
