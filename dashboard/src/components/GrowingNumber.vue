<template>
  <div>
    {{ prefix }}{{ newValueFormatted }}{{ suffix }}
  </div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from "vue-property-decorator";
import numeral from 'numeral'

@Component({
  name: 'GrowingNumber',

  watch: {
    value () {
      // TODO: FIX
      // this.growInit()
    }
  }
})
export default class GrowingNumber extends Vue {
  @Prop({
    type: String,
    default: null
  })
  prefix;

  @Prop({
    type: String,
    default: null
  })
  suffix;

  @Prop({
    type: Number,
    default: 0
  })
  value;

  @Prop({
    type: Number,
    default: 500
  })
  duration;

  newValue = 0;
  step = 0;

  get newValueFormatted() {
    return (this.newValue < 1000) ? this.newValue : numeral(this.newValue).format('0,0')
  }

  mounted() {
    this.growInit()
  }

  growInit() {
    const m = this.value / (this.duration / 25)
    this.grow(m)
  }

  grow(m) {
    const v = Math.ceil(this.newValue + m)

    if (v > this.value) {
      this.newValue = this.value
      return false
    }

    this.newValue = v
    setTimeout(() => {
      this.grow(m)
    }, 25)
  }
}
</script>
