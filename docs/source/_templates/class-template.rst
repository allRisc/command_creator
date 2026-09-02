{{ fullname | escape | underline}}

.. currentmodule:: {{ module }}

.. autoclass:: {{ objname }}
   :members:
   :private-members:
   :show-inheritance:

   {# Only summarise members declared on this class. Inherited members (e.g. pydantic
      BaseModel methods, or the ConfigDict keys a CmdConfig TypedDict inherits) are omitted:
      they are noise, and a TypedDict's inherited keys are not importable attributes, so
      autosummary would fail to resolve each one and break the -W docs build. #}
   {% block methods %}
   .. automethod:: __init__

   {% set own_methods = methods | reject("in", inherited_members) | list %}
   {% if own_methods %}
   .. rubric:: {{ _('Methods') }}

   .. autosummary::
   {% for item in own_methods %}
      ~{{ name }}.{{ item }}
   {%- endfor %}
   {% endif %}

   {% endblock %}

   {# CmdConfig and FieldKwargs are TypedDicts: their "attributes" are typing keys, not
      real class attributes, so Sphinx cannot tell inherited keys apart (inherited_members
      misses them) and autosummary fails to import each one, breaking the -W build. Their
      keys are still fully documented by the autoclass :members: body above, so skip the
      redundant summary table for them. #}
   {% block attributes %}
   {% if objname not in ["CmdConfig", "FieldKwargs"] %}
   {% set own_attributes = attributes | reject("in", inherited_members) | list %}
   {% if own_attributes %}
   .. rubric:: {{ _('Attributes') }}

   .. autosummary::
   {% for item in own_attributes %}
      ~{{ name }}.{{ item }}
   {%- endfor %}
   {% endif %}
   {% endif %}
   {% endblock %}