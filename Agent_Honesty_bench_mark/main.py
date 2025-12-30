import argparse
from datetime import datetime
from pathlib import Path

from Utils.benchmark_utils import load_benchmark_tasks
from Utils.config_utils import read_config
from Utils.environment_utils import normalize_environment_config, set_global_environment_context, archive_environment_resources
from Utils.agent_utils import create_agents
from Utils.tool_utils import load_grouped_tools
from Utils.result_utils import save_logs, save_results
from Utils.runner import run_all_tasks, run_interactive_mode, run_specific_task
from Utils.model_utils import create_model


def main():
    parser = argparse.ArgumentParser(description="Run the agent sandbox.")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to the config file.")
    parser.add_argument("--task", type=str, help="Specific task to run (optional).")
    parser.add_argument(
        "--interactive", action="store_true", help="Run in interactive mode."
    )
    args = parser.parse_args()

    try:
        config_path = Path(args.config).expanduser().resolve()
        config = read_config(config_path)
        print(f"Configuration file loaded successfully: {config_path}")
        repo_root = Path.cwd()
        environment_context = normalize_environment_config(config, repo_root)
        
        # Add benchmark path to environment context
        benchmark_path = config.get("Benchmark", {}).get("path", "")
        benchmark_name = config.get("Benchmark", {}).get("name", "")
        environment_context["benchmark_path"] = benchmark_path
        environment_context["benchmark_name"] = benchmark_name
        set_global_environment_context(environment_context)
        env_root_display = environment_context.get("base_path")
        print(
            f"Environment type: {environment_context.get('type')} "
            f"(root: {env_root_display})"
        )

        print("Creating model...")
        model = create_model(config)
        
        print("Creating Agent(s)...")
        agent_bundle = create_agents(config, model)
        agent = agent_bundle.primary
        managed_count = len(agent_bundle.managed)
        if managed_count:
            managed_names = []
            for managed_agent in agent_bundle.managed:
                managed_names.append(managed_agent.name or managed_agent.agent_name)
            print(
                f"Primary agent created successfully with {managed_count} managed agent(s): "
                f"{', '.join(managed_names)}"
            )
        else:
            print("Agent created successfully")

        benchmark_type = config.get("Benchmark", {}).get("type", "unknown")
        print(f"Benchmark type: {benchmark_type}")
        multi_turn = bool(config.get("Benchmark", {}).get("multi_turn"))

        if args.interactive:
            run_interactive_mode(agent, environment_context)
            return

        tasks = load_benchmark_tasks(config)
        print(f"Loaded {len(tasks)} tasks")
        if tasks:
            print(f"First task type: {type(tasks[0])}")
            print(f"First task content: {tasks[0]}")
        benchmark_config = config.get("Benchmark", {})
        per_task_tools = bool(benchmark_config.get("per_task_tools"))
        grouped_tools = load_grouped_tools(config) if per_task_tools else {}
        if not per_task_tools and grouped_tools:
            # Auto-enable if grouped tools are discoverable.
            per_task_tools = True
        start_idx = benchmark_config.get("start_idx")
        end_idx = benchmark_config.get("end_idx")

        output_config = config.get("Output", {})
        include_environment = output_config.get("include_environment", False)
        archive_dir = output_config.get("environment_archive_dir")
        archive_enabled = bool(archive_dir)

        if args.task:
            result, env_resources, steps, summary = run_specific_task(agent, args.task, environment_context)
            archive_metadata = None
            if archive_enabled:
                archive_metadata = archive_environment_resources(
                    env_resources,
                    archive_dir,
                    task_identifier=args.task or "ad-hoc",
                )
            results_payload = {
                "task": args.task,
                "result": str(result),
                "timestamp": datetime.now().isoformat(),
                "benchmark_type": benchmark_type,
                "environment_type": environment_context.get("type"),
            }
            if include_environment:
                results_payload["environment_resources"] = env_resources
            if archive_metadata:
                results_payload["environment_archive"] = archive_metadata
            results_payload.update(summary)
            save_results(config, results_payload)
            log_payload = {
                "task": args.task,
                "timestamp": results_payload["timestamp"],
                "benchmark_type": benchmark_type,
                "environment_type": environment_context.get("type"),
                "steps": steps,
            }
            if include_environment:
                log_payload["environment_resources"] = env_resources
            if archive_metadata:
                log_payload["environment_archive"] = archive_metadata
            log_payload.update(summary)
            save_logs(config, log_payload, label="single_task")
        else:
            retry_cfg = config.get("Retry", {}) if isinstance(config.get("Retry", {}), dict) else {}
            agent_retry_cfg = config.get("Agent", {}).get("Retry", {})
            # 兼容 Agent: 直接放 max_attempts 的配置
            agent_max_attempts = config.get("Agent", {}).get("max_attempts")
            if isinstance(agent_retry_cfg, dict) and agent_retry_cfg:
                retry_cfg = {**retry_cfg, **agent_retry_cfg}
            if agent_max_attempts is not None:
                retry_cfg.setdefault("max_attempts", agent_max_attempts)
            retry_attempts = int(retry_cfg.get("max_attempts", 1) or 1)
            all_results, all_logs = run_all_tasks(
                agent_bundle,
                tasks,
                benchmark_type,
                environment_context,
                include_environment=include_environment,
                archive_enabled=archive_enabled,
                archive_dir=archive_dir,
                start_idx=start_idx,
                end_idx=end_idx,
                per_task_tools=per_task_tools,
                grouped_tools=grouped_tools,
                retry_attempts=retry_attempts,
                multi_turn=multi_turn,
            )
            if all_results:
                save_results(config, all_results)
            if all_logs:
                log_label_parts = [benchmark_type or "batch"]
                if start_idx is not None:
                    log_label_parts.append(f"start{start_idx}")
                if end_idx is not None:
                    log_label_parts.append(f"end{end_idx}")
                save_logs(config, all_logs, label="_".join(log_label_parts))

    except Exception as exc:
        print(f"Program execution error: {exc}")
        import traceback

        traceback.print_exc()
        print("\n=== Full traceback ===")
        import sys
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)



if __name__ == "__main__":
    main()
