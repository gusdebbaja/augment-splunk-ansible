# Enhanced Splunk App Templates - Examples

This directory contains examples of the enhanced app templating system that supports both the new Terraform-style format and legacy backward compatibility.

## Enhanced Format (`enhanced-app-template-example.yml`)

The enhanced format supports:

- **Role-specific app generation**: One template generates multiple apps for different Splunk roles
- **Resource-based configuration**: Separate sections for indexers, search_heads, universal_forwarders, etc.
- **Built-in Splunk resource management**: Auto-generates indexes.conf, inputs.conf, serverclass.conf
- **Template references**: Support for sub-templates with specific template_vars
- **Enterprise metadata**: Business unit, cost center, classification, owner tracking

### Key Features:

1. **Multi-app generation**: One app.yml can generate:
   - `company1_TestPaymentService_indexer` (with indexes.conf)
   - `company1_payment-service-ops` (search head app)
   - `company1_payment-service-security` (search head app)
   - `company1_TestPaymentService_inputs` (universal forwarder inputs)
   - `company1_security-data-collection` (templated UF app)
   - `company1_TestPaymentService_serverclass` (deployment server config)

2. **Variable precedence** (highest to lowest):
   - app.yml template_vars
   - host vars (additional_template_vars)
   - group vars (template_vars)
   - environment vars
   - default vars

3. **Resource templates**: Auto-generates proper Splunk configurations
   - indexes.conf with retention, sizing, and advanced options
   - inputs.conf with all standard input parameters
   - serverclass.conf with deployment automation
   - app.conf with proper metadata

## Legacy Format (`legacy-app-template-example.yml`)

The legacy format maintains full backward compatibility:

- Single app generation per template
- splunk_roles targeting
- environments filtering
- Original template_vars structure

## Usage

Place either format in your `app-templates/` directory structure:

```
app-templates/
├── payment-service/
│   ├── app.yml                 # Enhanced or legacy format
│   ├── default/
│   │   └── some-config.conf.j2
│   └── analytics-dashboard/    # Sub-template for search heads
│       └── default/
│           └── data/
│               └── ui/
│                   └── views/
│                       └── dashboard.xml.j2
```

## Variable Merging

Both formats support the same variable merging hierarchy but the enhanced format adds more context-aware variables for each role type.

## Migration Path

1. **Immediate**: Use legacy format for existing templates
2. **Gradual**: Convert to enhanced format for new multi-role applications
3. **Advanced**: Leverage sub-templates and resource generation for complex apps