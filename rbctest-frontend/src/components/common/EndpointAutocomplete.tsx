import { Autocomplete, TextField, Chip } from "@mui/material";
import { useGetEndpointsQuery } from "@/services/api";

interface EndpointAutocompleteProps {
  value: string | string[];
  onChange: (value: string | string[]) => void;
  multiple?: boolean;
  label?: string;
  error?: boolean;
  helperText?: string;
}

export default function EndpointAutocomplete({
  value,
  onChange,
  multiple = false,
  label = "Select Endpoint",
  error,
  helperText,
}: EndpointAutocompleteProps) {
  const { data: endpointsData, isLoading } = useGetEndpointsQuery({
    limit: 1000,
    offset: 0,
  });
  const endpoints = endpointsData?.endpoints || [];

  return (
    <Autocomplete
      multiple={multiple}
      options={endpoints}
      getOptionLabel={(option) => (option as any).name}
      value={
        multiple
          ? endpoints.filter((e) => (value as string[]).includes(e.name))
          : endpoints.find((e) => e.name === value) || null
      }
      onChange={(_, newValue) => {
        if (multiple) {
          onChange((newValue as any[]).map((v) => v.name));
        } else {
          onChange(newValue ? (newValue as any).name : "");
        }
      }}
      loading={isLoading}
      renderInput={(params) => {
        const { InputLabelProps, ...otherParams } = params;
        return (
          <TextField
            {...otherParams}
            label={label}
            error={error || false}
            helperText={helperText}
            size="small"
          />
        );
      }}
      renderTags={(value, getTagProps) =>
        value.map((option, index) => (
          <Chip
            label={(option as any).name}
            {...getTagProps({ index })}
            size="small"
          />
        ))
      }
    />
  );
}
