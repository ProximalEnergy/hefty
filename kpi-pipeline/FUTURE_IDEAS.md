## Registry

Group classes into registries by protocol (i.e. process, calculation, transform registries).

The benefits of a registry would be:

- accessing classes easily through a registry instead of hunting down where the import statement
  should come from
- we can organize classes wherever we want to in the code but still have the classes gathered into
  a single collection.
- With some additional work configurations could be loaded and saved using the name of the class in the
  registry.

Here's an idea for a generic registry object

```

E = TypeVar("E", bound=Enum)
T = TypeVar("T")


class Registry[E, T]:
    def __init__(self):
        self._registry = {}

    @property
    def register_class(self):
        def decorator(
            original_class,
        ):
            self._registry[original_class._registered_name] = original_class
            original_class = save_init_args(original_class)
            return original_class

        return decorator

    def __getitem__(self, key: str):
        return self._registry[key]

    def __contains__(self, key: str) -> bool:
        return key in self._registry

    def from_json_like(self, json_like):
        if json_like is None:
            return None
        method = json_like.get("name", IDENTITY)
        params = json_like.get("params", {})
        instance = self._registry[method].from_json_like(json_like=params)
        return instance
```

These are some of the other functions that would be necessary to load and save a configuration

```

def save_init_args(cls):
    """
    A class decorator that automatically captures and saves the arguments
    passed to a class's __init__ method in an `_init_args` attribute.
    """
    # Get the original __init__ method and its signature
    original_init = cls.__init__
    init_signature = inspect.signature(original_init)

    # Define a new __init__ method (a wrapper)
    @wraps(original_init)
    def wrapper_init(self, *args, **kwargs):
        # Use the signature to bind the passed arguments
        bound_args = init_signature.bind(self, *args, **kwargs)
        # bound_args.apply_defaults()

        # Store the arguments dictionary on the instance
        self._init_args = bound_args.arguments
        self._init_args.pop("self", None)  # Remove 'self'

        # Call the original __init__ method to run its logic
        original_init(self, *args, **kwargs)

    # Replace the class's __init__ with our new wrapper
    cls.__init__ = wrapper_init
    return cls


class Registered:
    _registered_name: str
    _init_args: dict

    @classmethod
    def from_json_like(cls, json_like):
        instance = cls(**json_like)
        return instance

    def json_init_args(self):
        return {}

    def get_init_args(self):
        args = self._init_args.copy()
        args.update(self.json_init_args())
        return args

    def to_json_like(self):
        result = {}
        if self._registered_name != IDENTITY:
            result["name"] = self._registered_name
        init_args = self.get_init_args()
        if init_args:
            result["params"] = init_args
        return result

class RegisteredClassProtocol(Protocol):
    # provided explicitly
    _registered_name: str
    __call__: Callable

    # added by decorators
    _init_args: dict

    @classmethod
    def from_json_like(cls, json_like) -> Self: ...

    def to_json_like(self) -> dict: ...


```

The `Registered` class sketches out the abstract class for registered classes.

## Static Field Analysis

Equip calculation classes with the ability to know which fields are required and equip
transforms to know which fields are required and what fields are produced.

Here is the abstract class for the calculation

```

class CalcAbstract(ABC):
    @abstractmethod
    def required_fields(self):
        pass

    @abstractmethod
    def __call__(self, *, dataset: xr.Dataset, context: Context):
        pass
```

and here is the abstract class for a transformation

```

class TransformAbstract(ABC):
    @abstractmethod
    def expected_outputs(
        self, previous_outputs: Optional[list[str]] = None
    ) -> list[str]:
        pass

    @abstractmethod
    def expected_inputs(self, next_inputs: Optional[list[str]] = None) -> list[str]:
        pass

    @abstractmethod
    def required_fields(
        self, output_fields: list[str], observer: Observer
    ) -> list[str]:
        pass

    @abstractmethod
    def resulting_fields(
        self, input_fields: list[str], observer: Observer
    ) -> list[str]:
        pass

    @abstractmethod
    def __call__(self, *, dataset: xr.Dataset, context: Context):
        pass
```

### Storing Pipelines

Once the transforms and calculations can be represented in a json format, it's possible
to not only store the overall KPI calculation tree, but segments of the tree as well.
At the time that the overall pipeline is exported, snippets of the tree can be separately
exported so that you can have, say, an RTE dedicated pipeline that includes cleaning,
intermediate steps, and final calculation that matches the overall KPI pipeline exactly.

Adapters can then be built around these generalized json snippets so that you can request
RTE, c-rate, or performance ratio and provide the inputs as pandas dataframes or xarrays.

This is how to collapse device information

```
dataset.current_dc_combiner_amps.groupby("pcs_by_dc_combiner").mean().rename({"pcs_by_dc_combiner": "pcs"})
```

This is how to expand device information

```
dataset.active_power_pcs.sel(pcs=dataset.coords['pcs_by_dc_combiner'])
```
