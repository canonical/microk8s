package v1

import "bytes"

// RestartServiceField is the "restart" field of the ConfigureServiceRequest message.
type RestartServiceField bool

// UnmarshalJSON implements json.Unmarshaler.
// It handles both boolean values, as well as the string value "yes".
func (v *RestartServiceField) UnmarshalJSON(b []byte) error {
	*v = RestartServiceField(bytes.Equal(b, []byte("true")) || bytes.Equal(b, []byte(`"yes"`)))
	return nil
}
