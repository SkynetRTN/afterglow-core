<template>
  <card-component class="is-card-widget" :icon="trendingIcon" :has-button-slot="true" :has-title-slot="true">
    <span slot="title">
      <b>{{ previousValue }}</b> in <b>{{ previousPeriod }}</b>
    </span>
    <!-- <button type="button" class="button is-small" slot="button" @click="buttonClick">
      <b-icon icon="settings" custom-size="default"/>
    </button> -->
    <div class="level is-mobile">
      <div class="level-item">
        <div class="is-widget-label">
          <h3 class="subtitle is-spaced">
            {{ label }}
          </h3>
          <h1 class="title">
            <growing-number :value="number" :prefix="prefix" :suffix="suffix"/>
          </h1>
        </div>
      </div>
      <div v-if="icon" class="level-item has-widget-icon">
        <div class="is-widget-icon">
          <b-icon :icon="icon" size="is-large" :type="type"/>
        </div>
      </div>
    </div>
  </card-component>
</template>

<script lang="ts">
import { Vue, Component, Prop } from "vue-property-decorator";
import numeral from 'numeral'
import CardComponent from './CardComponent.vue'
import GrowingNumber from './GrowingNumber.vue'
@Component({
  name: 'CardWidget',
  components: { GrowingNumber, CardComponent }
})
export default class CardWidget extends Vue {
  @Prop({
    type: String,
    default: null
  })
  icon;

  @Prop({
    type: Number,
    default: 0
  })
  number;

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
    type: String,
    default: null
  })
  label;

  @Prop({
    type: String,
    default: null
  })
  type;

  @Prop({
    type: Number,
    default: 0
  })
  previousNumber;

  @Prop({
    type: String,
    default: null
  })
  previousPeriod;

  get trendingIcon() {
    return (this.previousNumber < this.number) ? 'arrow-up-bold' : 'arrow-down-bold'
  }

  get previousValue() {
    let valueString = (this.previousNumber < 1000) ? this.previousNumber : numeral(this.previousNumber).format('0,0')

    if (this.prefix) {
      valueString = this.prefix + valueString
    }

    if (this.suffix) {
      valueString += this.suffix
    }

    return valueString
  }

  buttonClick() {
    this.$buefy.snackbar.open({
      message: 'Got click',
      queue: false
    })
  }
}
</script>
