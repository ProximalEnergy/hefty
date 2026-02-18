from typing import Self

import xarray as xr
from core.database import with_db
from core.enumerations import KPIType
from core.models import KPIInstance

from kpi_pipeline.base.models import ContextModel, KPIMetadata
from kpi_pipeline.base.protocols import (
    ActionProtocol,
    ObserverProtocol,
    TransformProtocol,
)
from kpi_pipeline.infra.data_access.utils import (
    get_application_name,
    insert_device_kpi_data_bulk,
)
from kpi_pipeline.infra.data_access.write import arrays_to_rows
from kpi_pipeline.services.action.utils import (
    is_identity,
    through_outputs,
)


class EmptyAction(ActionProtocol[None]):
    pass_through = False

    def __call__(
        self, *, dataset: xr.Dataset, context: ContextModel, observer: ObserverProtocol
    ) -> None:
        return None

    def nominal_outputs(self) -> list[str]:
        return []

    def expected_inputs(self, *, outputs: list[str] = []) -> list[str]:
        return []

    def trim(self, *, outputs: list[str] = []) -> Self:
        return self


class TransformAction[T](ActionProtocol[T]):
    def __init__(
        self,
        *,
        transform: TransformProtocol | None = None,
        action: ActionProtocol[T],
    ):
        self.transform = transform
        self.action = action

    def __call__(
        self, *, dataset: xr.Dataset, context: ContextModel, observer: ObserverProtocol
    ) -> T:
        if self.transform is not None:
            dataset = self.transform(
                dataset=dataset, context=context, observer=observer
            )
        return self.action(dataset=dataset, context=context, observer=observer)

    @property
    def pass_through(self) -> bool:
        return (
            self.transform is None or self.transform.pass_through
        ) and self.action.pass_through

    def nominal_outputs(self) -> list[str]:
        previous_outputs = []
        if self.transform is not None:
            previous_outputs = through_outputs(
                transform=self.transform, previous_outputs=previous_outputs
            )
        return through_outputs(transform=self.action, previous_outputs=previous_outputs)

    def expected_inputs(self, *, outputs: list[str] = []) -> list[str]:
        inputs = self.action.expected_inputs(outputs=outputs)
        if self.transform is not None:
            inputs = self.transform.expected_inputs(outputs=inputs)
        return inputs

    def trim(self, *, outputs: list[str] = []) -> Self:
        new_action = self.action.trim(outputs=outputs)
        new_transform = None
        if self.transform is not None:
            required_inputs = self.action.expected_inputs(outputs=outputs)
            new_transform = self.transform.trim(outputs=required_inputs)
            if is_identity(new_transform):
                new_transform = None
        return self.__class__(
            transform=new_transform,
            action=new_action,
        )


class UploadKpiAction(ActionProtocol[None]):
    pass_through = False

    def __init__(self, *, kpi_fields: dict[KPIType, KPIMetadata]):
        self.kpi_fields = kpi_fields

    def __call__(
        self, *, dataset: xr.Dataset, context: ContextModel, observer: ObserverProtocol
    ) -> None:
        project = context.project
        with with_db(schema=None) as db:
            kpi_instances = db.query(KPIInstance).filter(
                KPIInstance.project_id == project.project_id
            )
            kpi_type_ids = [r.kpi_type_id for r in kpi_instances]

        data_rows = []

        for kpi_type, kpi_metadata in self.kpi_fields.items():
            with observer.watch(
                var=kpi_type.name,
            ):
                if kpi_type.value not in kpi_type_ids:
                    observer.log(
                        message=f"KPI {repr(kpi_type)} has no instance for project {project.name_short}"
                    )
                    continue
                data_rows.extend(
                    arrays_to_rows(
                        dataset,
                        project.project_id,
                        kpi_type,
                        kpi_metadata,
                        start=context.start_date,
                        end=context.end_date,
                    )
                )

        insert_device_kpi_data_bulk(
            application_name=get_application_name(),
            data_rows=data_rows,
        )

    def nominal_outputs(self) -> list[str]:
        return [kpi_type.name for kpi_type in self.kpi_fields.keys()]

    def expected_inputs(self, *, outputs: list[str] = []) -> list[str]:
        project_fields = [
            kpi_field.project_var
            for kpi_type, kpi_field in self.kpi_fields.items()
            if kpi_type.name in outputs
        ]
        device_fields = [
            kpi_field.device_var
            for kpi_type, kpi_field in self.kpi_fields.items()
            if kpi_type.name in outputs and kpi_field.device_var is not None
        ]
        return list(set(project_fields + device_fields))

    def trim(self, *, outputs: list[str] = []) -> Self:
        return self.__class__(
            kpi_fields={
                kpi_type: kpi_field
                for kpi_type, kpi_field in self.kpi_fields.items()
                if kpi_type.name in outputs
            },
        )
