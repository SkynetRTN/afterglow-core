<template>
  <b-field grouped group-multiline>
    <div v-for="(v,k) in options" class="control" :key="k">
      <b-radio v-model="newValue" :native-value="k" @input="input" :type="type">
        {{ v }}
      </b-radio>
    </div>
  </b-field>
</template>

<script lang="ts">
import { Vue, Component, Prop } from "vue-property-decorator";
@Component({
  name: 'RadioPicker',

  watch: {
    value (newValue) {
      // TODO: FIX
      // this.newValue = newValue
    }
  }
})
export default class RadioPicker extends Vue {
  @Prop({
    type: Object,
    default: null
  })
  options;

  @Prop({
    type: String,
    default: null
  })
  type;

  @Prop({
    default: null
  })
  value;

  newValue = null;

  created() {
    this.newValue = this.value
  }

  input() {
    this.$emit('input', this.newValue)
  }
}
</script>
