#!/usr/bin/env python3
"""Detailed memory profiling script for pv-expected-energy application.
This script instruments the main simulation steps to identify memory hotspots.
"""

import asyncio
import gc
import logging
import os
import sys
import time
import traceback
import tracemalloc
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, cast

import psutil

# Add src to path so we can import the main module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from _utils.logger import setup_logger
from p00_parse_input.simulation_temporal_mode import SimulationTemporalMode
from p01_get_data.class_simulation_inputs import SimulationInputs
from p02_simulation._utils.known_exception import KnownException
from p02_simulation.c_simulate_project import simulate_project
from p02_simulation.p2_poai.c_poai import PlaneOfArrayIrradiance
from p02_simulation.p3_epoai.s01_direct_shade import ModelCircumsolar
from p02_simulation.p3_epoai.s05_soiling import ModelSoiling
from p02_simulation.p4_dc_iv.c_dc_iv import PowerAtCombiner
from p02_simulation.p4_dc_iv.s02_single_diode_params import ModelSingleDiode
from p02_simulation.p4_dc_iv.s04_iv_2_warranted_degradation import ModelDegradation
from p02_simulation.p4_dc_iv.s06_iv_4_dc_wiring_to_combiner import (
    ModelDCWiringToCombiner,
)
from p02_simulation.p5_inverter.c_inverter import InverterPower
from p02_simulation.p5_inverter.s00_dc_wiring_to_inverter import ModelDCWiringToInverter
from p02_simulation.p6_transformer.c_transformer import TransformerPower
from p02_simulation.p8_poi.c_poi import ProjectPower
from p03_export.c_export import export_simulation_results

logger = logging.getLogger(__name__)


class DetailedMemoryProfiler:
    """Enhanced memory profiler that tracks memory usage at each simulation step."""

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.memory_timeline: list[tuple[str, float, float, float]] = []
        self.step_memory_usage: dict[str, dict[str, Any]] = {}
        self.start_time = time.time()

    def get_memory_info(self) -> tuple[float, float]:
        """Get current memory usage in MB (RSS and VMS)."""
        memory_info = self.process.memory_info()
        rss_mb = memory_info.rss / 1024 / 1024  # Resident Set Size
        vms_mb = memory_info.vms / 1024 / 1024  # Virtual Memory Size
        return rss_mb, vms_mb

    @contextmanager
    def profile_step(self, step_name: str) -> Generator[None, None, None]:
        """Context manager to profile memory usage of a simulation step."""
        # Force garbage collection before measuring
        gc.collect()

        start_rss, start_vms = self.get_memory_info()
        start_time = time.time()
        elapsed_from_start = start_time - self.start_time

        # Get tracemalloc snapshot if available
        start_tracemalloc = None
        if tracemalloc.is_tracing():
            start_tracemalloc = tracemalloc.take_snapshot()

        logger.info(f"\n🔍 Starting '{step_name}'")
        logger.info(f"   Memory before: RSS={start_rss:.2f} MB, VMS={start_vms:.2f} MB")

        try:
            yield

        finally:
            end_time = time.time()
            end_rss, end_vms = self.get_memory_info()
            duration = end_time - start_time
            rss_delta = end_rss - start_rss
            vms_delta = end_vms - start_vms

            # Calculate memory delta from tracemalloc if available
            tracemalloc_delta = 0
            if start_tracemalloc and tracemalloc.is_tracing():
                end_tracemalloc = tracemalloc.take_snapshot()
                top_stats = end_tracemalloc.compare_to(start_tracemalloc, "lineno")
                tracemalloc_delta = (
                    sum(stat.size_diff for stat in top_stats) / 1024 / 1024
                )

            # Store step metrics
            self.step_memory_usage[step_name] = {
                "start_rss_mb": start_rss,
                "end_rss_mb": end_rss,
                "rss_delta_mb": rss_delta,
                "start_vms_mb": start_vms,
                "end_vms_mb": end_vms,
                "vms_delta_mb": vms_delta,
                "duration_seconds": duration,
                "tracemalloc_delta_mb": tracemalloc_delta,
                "elapsed_from_start": elapsed_from_start,
            }

            # Add to timeline
            self.memory_timeline.append(
                (step_name, elapsed_from_start, end_rss, duration)
            )

            logger.info(f"✅ Completed '{step_name}'")
            logger.info(
                f"   Memory after: RSS={end_rss:.2f} MB, VMS={end_vms:.2f} MB"
            )
            logger.info(
                f"   Memory delta: RSS={rss_delta:+.2f} MB, VMS={vms_delta:+.2f} MB"
            )
            logger.info(f"   Duration: {duration:.2f} seconds")
            if tracemalloc_delta != 0:
                logger.info(f"   Tracemalloc delta: {tracemalloc_delta:+.2f} MB")

    def print_detailed_summary(self):
        """Print comprehensive memory usage analysis."""
        logger.info("\n" + "=" * 100)
        logger.info("🎯 DETAILED MEMORY ANALYSIS SUMMARY")
        logger.info("=" * 100)

        if not self.step_memory_usage:
            logger.info("No memory data collected.")
            return

        # Sort steps by RSS memory delta (descending)
        sorted_steps = sorted(
            self.step_memory_usage.items(),
            key=lambda x: x[1]["rss_delta_mb"],
            reverse=True,
        )

        logger.info(
            f"{'Step Name':<30} {'RSS Δ (MB)':<12} {'VMS Δ (MB)':<12} "
            f"{'Duration (s)':<12} {'Peak RSS (MB)':<15}"
        )
        logger.info("-" * 100)

        for step_name, stats in sorted_steps:
            logger.info(
                f"{step_name:<30} {stats['rss_delta_mb']:>+10.2f} "
                f"{stats['vms_delta_mb']:>+10.2f} "
                f"{stats['duration_seconds']:>10.2f} "
                f"{stats['end_rss_mb']:>13.2f}"
            )

        logger.info("\n📈 Memory Timeline:")
        logger.info("-" * 60)
        logger.info(
            f"{'Time (s)':<10} {'Step':<30} {'RSS (MB)':<12} "
            f"{'Duration (s)':<12}"
        )
        logger.info("-" * 60)

        for step_name, elapsed, rss, duration in self.memory_timeline:
            logger.info(
                f"{elapsed:>8.1f} {step_name:<30} {rss:>10.2f} "
                f"{duration:>10.2f}"
            )

        logger.info("\n🔥 Top Memory Consumers (by RSS delta):")
        logger.info("-" * 50)

        for i, (step_name, stats) in enumerate(sorted_steps[:10], 1):
            if stats["rss_delta_mb"] > 0:
                logger.info(
                    f"{i:>2}. {step_name:<25}: +{stats['rss_delta_mb']:>8.2f} MB "
                    f"RSS ({stats['duration_seconds']:>6.2f}s)"
                )

        # Summary statistics
        total_rss_increase = sum(
            stats["rss_delta_mb"]
            for stats in self.step_memory_usage.values()
            if stats["rss_delta_mb"] > 0
        )
        total_duration = sum(
            stats["duration_seconds"] for stats in self.step_memory_usage.values()
        )
        peak_rss = max(stats["end_rss_mb"] for stats in self.step_memory_usage.values())

        logger.info("\n📊 Summary Statistics:")
        logger.info(f"   Total RSS increase: {total_rss_increase:.2f} MB")
        logger.info(f"   Peak RSS usage: {peak_rss:.2f} MB")
        logger.info(f"   Total duration: {total_duration:.2f} seconds")
        logger.info(f"   Steps analyzed: {len(self.step_memory_usage)}")


async def detailed_simulation_with_profiling():
    """Run simulation with detailed step-by-step memory profiling."""
    profiler = DetailedMemoryProfiler()
    setup_logger(level=logging.INFO, environment="DEV")

    # Start tracemalloc for detailed tracking
    tracemalloc.start()

    logger.info("🚀 Starting Detailed Memory Profiling of PV Simulation")
    logger.info("=" * 70)

    initial_rss, initial_vms = profiler.get_memory_info()
    logger.info(
        f"📊 Initial memory: RSS={initial_rss:.2f} MB, VMS={initial_vms:.2f} MB"
    )

    try:
        # Setup logging
        with profiler.profile_step("Setup Logging"):
            setup_logger()

        # Get simulation inputs
        with profiler.profile_step("Load Simulation Config"):
            simulation_inputs: SimulationInputs = (
                await SimulationInputs.from_proximal_db(
                    project_name_short="sigurd",
                    simulation_temporal_mode=SimulationTemporalMode.WINDOW,
                    simulation_start="2025-09-20 00:00:00",
                    simulation_end="2025-09-20 23:55:00",
                    sun_position_offset=0,
                    use_poa_only=True,
                    soiling=ModelSoiling.NONE,
                    degradation=ModelDegradation.WARRANTED,
                    single_diode_model=ModelSingleDiode.PVWATTS,
                    circumsolar=ModelCircumsolar.DIFFUSE,
                    dc_wiring_to_combiner=ModelDCWiringToCombiner.TARGET_STC,
                    dc_wiring_to_inverter=ModelDCWiringToInverter.TARGET_STC,
                )
            )

        # Create simulation generator
        with profiler.profile_step("Create Simulation Generator"):
            simulation = simulate_project(inputs=simulation_inputs)

        # Step 1: Plane of Array Irradiance (POAI)
        with profiler.profile_step("POAI Calculation"):
            poai: PlaneOfArrayIrradiance = cast(
                PlaneOfArrayIrradiance, next(simulation)
            )

        with profiler.profile_step("Export POAI Results"):
            export_simulation_results(
                results=poai,
                project_name_short="sigurd",
                simulation_start="2025-09-20 00:00:00",
                simulation_config=simulation_inputs.simulation_config,
                engine=simulation_inputs.engine,
                version=simulation_inputs.version,
                ENVIRONMENT=simulation_inputs.ENVIRONMENT,
            )

        # Step 2: Power at Combiner
        with profiler.profile_step("Combiner Power Calculation"):
            combiners: PowerAtCombiner = cast(PowerAtCombiner, next(simulation))

        with profiler.profile_step("Export Combiner Results"):
            export_simulation_results(
                results=combiners,
                project_name_short="sigurd",
                simulation_start="2025-09-20 00:00:00",
                simulation_config=simulation_inputs.simulation_config,
                engine=simulation_inputs.engine,
                version=simulation_inputs.version,
                ENVIRONMENT=simulation_inputs.ENVIRONMENT,
            )

        # Step 3: Inverter Power
        with profiler.profile_step("Inverter Power Calculation"):
            inverters: InverterPower = cast(InverterPower, next(simulation))

        with profiler.profile_step("Export Inverter Results"):
            export_simulation_results(
                results=inverters,
                project_name_short="sigurd",
                simulation_start="2025-09-20 00:00:00",
                simulation_config=simulation_inputs.simulation_config,
                engine=simulation_inputs.engine,
                version=simulation_inputs.version,
                ENVIRONMENT=simulation_inputs.ENVIRONMENT,
            )

        # Step 4: Transformer Power
        with profiler.profile_step("Transformer Power Calculation"):
            _transformers: TransformerPower = cast(
                TransformerPower, next(simulation)
            )

        # Step 5: Point of Interconnection (POI)
        with profiler.profile_step("POI Power Calculation"):
            poi: ProjectPower = cast(ProjectPower, next(simulation))

        with profiler.profile_step("Export POI Results"):
            export_simulation_results(
                results=poi,
                project_name_short="sigurd",
                simulation_start="2025-09-20 00:00:00",
                simulation_config=simulation_inputs.simulation_config,
                engine=simulation_inputs.engine,
                version=simulation_inputs.version,
                ENVIRONMENT=simulation_inputs.ENVIRONMENT,
            )

        # Print memory analysis
        current, peak = tracemalloc.get_traced_memory()
        final_rss, final_vms = profiler.get_memory_info()

        logger.info("\n🏁 Final Memory State:")
        logger.info(
            f"   Final RSS: {final_rss:.2f} MB "
            f"(Δ{final_rss - initial_rss:+.2f} MB)"
        )
        logger.info(
            f"   Final VMS: {final_vms:.2f} MB "
            f"(Δ{final_vms - initial_vms:+.2f} MB)"
        )
        logger.info(f"   Tracemalloc current: {current / 1024 / 1024:.2f} MB")
        logger.info(f"   Tracemalloc peak: {peak / 1024 / 1024:.2f} MB")

        profiler.print_detailed_summary()

        return {"status_code": 200, "message": "Detailed profiling complete"}

    except KnownException as ke:
        logger.info(f"⚠️ Known exception: {ke}")
        return {"status_code": ke.error_type.value, "message": str(ke)}

    except Exception as e:
        logger.info(f"❌ Error during simulation: {e}")
        traceback.print_exc()
        return {"status_code": 500, "message": str(e)}

    finally:
        tracemalloc.stop()


if __name__ == "__main__":
    logger.info("🔬 PV Expected Energy - Detailed Memory Profiler")
    logger.info("=" * 60)

    try:
        result = asyncio.run(detailed_simulation_with_profiling())
        logger.info("\n✅ Detailed profiling completed!")
        logger.info(f"Result: {result}")

    except KeyboardInterrupt:
        logger.info("\n⚠️ Profiling interrupted by user")
    except Exception as e:
        logger.info(f"\n❌ Profiling failed: {e}")
        sys.exit(1)
